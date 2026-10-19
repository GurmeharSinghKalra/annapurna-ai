"""Farmer accounts: registration, login, token refresh, profile, and account deletion.

Guest use of Annapurna is unchanged. An account only adds durable, multi-device storage for
saved plans and season budgets; no planning route requires one.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import delete, select, update

from ..deps import CurrentFarmerDep, SessionDep, rate_limit
from ..models import Farmer, RefreshSession
from ..security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    normalise_phone,
    password_problem,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# A dummy verification target so a login attempt against an unknown phone number costs the same
# time as one against a real account, which stops the endpoint confirming who is registered.
_DUMMY_HASH = hash_password("annapurna-timing-equaliser")

_BAD_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Phone number or password is incorrect",
)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=200)
    email: EmailStr | None = None
    language: Literal["English", "Hindi", "Punjabi", "Haryanvi"] = "English"
    location: str = Field(default="", max_length=120)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        try:
            return normalise_phone(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        problem = password_problem(value)
        if problem:
            raise ValueError(problem)
        return value


class LoginRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        try:
            return normalise_phone(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    language: Literal["English", "Hindi", "Punjabi", "Haryanvi"] | None = None
    location: str | None = Field(default=None, max_length=120)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        problem = password_problem(value)
        if problem:
            raise ValueError(problem)
        return value


class FarmerOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    email: str | None
    language: str
    location: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    farmer: FarmerOut


def _farmer_out(farmer: Farmer) -> FarmerOut:
    return FarmerOut(
        id=farmer.id,
        name=farmer.name,
        phone=farmer.phone,
        email=farmer.email,
        language=farmer.language,
        location=farmer.location,
        created_at=farmer.created_at,
    )


async def _issue_tokens(session: SessionDep, farmer: Farmer, request: Request) -> TokenPair:
    access_token, expires_in = create_access_token(farmer.id)
    raw_refresh, refresh_hash, refresh_expires = new_refresh_token()
    session.add(
        RefreshSession(
            farmer_id=farmer.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires,
            user_agent=(request.headers.get("user-agent") or "")[:200] or None,
        )
    )
    farmer.last_login_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(farmer)
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=expires_in,
        farmer=_farmer_out(farmer),
    )


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth-register", limit=5, window_seconds=3600))],
)
async def register(payload: RegisterRequest, session: SessionDep, request: Request) -> TokenPair:
    existing = await session.scalar(select(Farmer.id).where(Farmer.phone == payload.phone))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This phone number already has an account")
    if payload.email:
        email_taken = await session.scalar(select(Farmer.id).where(Farmer.email == payload.email))
        if email_taken is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email already has an account")

    farmer = Farmer(
        name=payload.name.strip(),
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
        language=payload.language,
        location=payload.location.strip(),
    )
    session.add(farmer)
    await session.flush()
    return await _issue_tokens(session, farmer, request)


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit("auth-login", limit=10, window_seconds=900))],
)
async def login(payload: LoginRequest, session: SessionDep, request: Request) -> TokenPair:
    farmer = await session.scalar(select(Farmer).where(Farmer.phone == payload.phone))
    if farmer is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise _BAD_CREDENTIALS

    is_valid, replacement = verify_password(payload.password, farmer.password_hash)
    if not is_valid:
        raise _BAD_CREDENTIALS
    if not farmer.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled")
    if replacement:
        farmer.password_hash = replacement
    return await _issue_tokens(session, farmer, request)


@router.post(
    "/refresh",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit("auth-refresh", limit=60, window_seconds=900))],
)
async def refresh(payload: RefreshRequest, session: SessionDep, request: Request) -> TokenPair:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = await session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
    if stored is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")

    if not stored.is_usable:
        # A revoked token being replayed means the token leaked. Drop every session for the
        # account so the attacker and the farmer are both forced to sign in again.
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.farmer_id == stored.farmer_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")

    farmer = await session.get(Farmer, stored.farmer_id)
    if farmer is None or not farmer.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")

    stored.revoked_at = datetime.now(UTC)  # Rotate: one refresh token is usable exactly once.
    return await _issue_tokens(session, farmer, request)


@router.post("/logout", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, session: SessionDep) -> None:
    await session.execute(
        update(RefreshSession)
        .where(RefreshSession.token_hash == hash_refresh_token(payload.refresh_token))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


@router.get("/me", response_model=FarmerOut)
async def me(farmer: CurrentFarmerDep) -> FarmerOut:
    return _farmer_out(farmer)


@router.patch("/me", response_model=FarmerOut)
async def update_me(payload: ProfileUpdate, farmer: CurrentFarmerDep, session: SessionDep) -> FarmerOut:
    if payload.email and payload.email != farmer.email:
        taken = await session.scalar(select(Farmer.id).where(Farmer.email == payload.email, Farmer.id != farmer.id))
        if taken is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email already has an account")
    for field in ("name", "email", "language", "location"):
        value = getattr(payload, field)
        if value is not None:
            setattr(farmer, field, value.strip() if isinstance(value, str) else value)
    await session.commit()
    await session.refresh(farmer)
    return _farmer_out(farmer)


@router.post("/password", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def change_password(payload: PasswordChange, farmer: CurrentFarmerDep, session: SessionDep) -> None:
    is_valid, _ = verify_password(payload.current_password, farmer.password_hash)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    farmer.password_hash = hash_password(payload.new_password)
    # Changing a password must end every other signed-in session.
    await session.execute(
        update(RefreshSession)
        .where(RefreshSession.farmer_id == farmer.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


@router.delete("/me", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(farmer: CurrentFarmerDep, session: SessionDep) -> None:
    """Delete the account and every record owned by it, immediately and irreversibly."""
    await session.execute(delete(Farmer).where(Farmer.id == farmer.id))
    await session.commit()
