"""Durable, account-scoped records: saved crop plans and season budgets.

Every query is filtered by the signed-in farmer's id, so one account can never read or modify
another's rows even when an id is guessed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from ..deps import CurrentFarmerDep, SessionDep, rate_limit
from ..models import FarmProfileRecord, SavedPlan, SeasonFinancePlan
from ..schemas import FarmProfile, Recommendation

router = APIRouter(tags=["records"])

MAX_PLANS_PER_FARMER = 200
MAX_PROFILES_PER_FARMER = 25


class SavePlanRequest(BaseModel):
    farm: FarmProfile
    recommendation: Recommendation
    weather: dict[str, Any] | None = None
    soil: dict[str, Any] | None = None
    market: dict[str, Any] | None = None
    ai_explanation: dict[str, Any] | None = None
    note: str | None = Field(default=None, max_length=280)


class SavedPlanOut(BaseModel):
    id: uuid.UUID
    crop: str
    suitability: int
    expected_profit: int
    location: str
    season: str
    note: str | None
    created_at: datetime
    farm_snapshot: dict[str, Any]
    recommendation: dict[str, Any]
    weather: dict[str, Any] | None
    soil: dict[str, Any] | None
    market: dict[str, Any] | None
    ai_explanation: dict[str, Any] | None


class SavedPlanSummary(BaseModel):
    id: uuid.UUID
    crop: str
    suitability: int
    expected_profit: int
    location: str
    season: str
    note: str | None
    created_at: datetime


class PlanPage(BaseModel):
    items: list[SavedPlanSummary]
    total: int
    limit: int
    offset: int


class SaveFinancePlanRequest(BaseModel):
    farm: FarmProfile
    plan: dict[str, Any]
    saved_plan_id: uuid.UUID | None = None
    actual_expenses: dict[str, float] = Field(default_factory=dict, max_length=12)
    market_price_per_quintal: int | None = Field(default=None, ge=1, le=1_000_000)


class FinancePlanOut(BaseModel):
    id: uuid.UUID
    crop: str
    planning_source: str
    market_price_per_quintal: int | None
    actual_expenses: dict[str, Any]
    plan: dict[str, Any]
    saved_plan_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ProfileRequest(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    farm: FarmProfile
    is_default: bool = False


class ProfileOut(BaseModel):
    id: uuid.UUID
    label: str
    is_default: bool
    farm: dict[str, Any]
    created_at: datetime
    updated_at: datetime


def _plan_out(row: SavedPlan) -> SavedPlanOut:
    return SavedPlanOut(
        id=row.id,
        crop=row.crop,
        suitability=row.suitability,
        expected_profit=row.expected_profit,
        location=row.location,
        season=row.season,
        note=row.note,
        created_at=row.created_at,
        farm_snapshot=row.farm_snapshot,
        recommendation=row.recommendation,
        weather=row.weather,
        soil=row.soil,
        market=row.market,
        ai_explanation=row.ai_explanation,
    )


def _finance_out(row: SeasonFinancePlan) -> FinancePlanOut:
    return FinancePlanOut(
        id=row.id,
        crop=row.crop,
        planning_source=row.planning_source,
        market_price_per_quintal=row.market_price_per_quintal,
        actual_expenses=row.actual_expenses,
        plan=row.plan,
        saved_plan_id=row.saved_plan_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _profile_out(row: FarmProfileRecord) -> ProfileOut:
    farm = {
        column: getattr(row, column)
        for column in (
            "farmer_name",
            "location",
            "language",
            "land_size",
            "season",
            "previous_crop",
            "soil_type",
            "ph",
            "nitrogen",
            "phosphorus",
            "potassium",
            "temperature",
            "humidity",
            "rainfall",
            "budget",
            "market_priority",
        )
    }
    return ProfileOut(
        id=row.id,
        label=row.label,
        is_default=row.is_default,
        farm=farm,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post(
    "/plans",
    response_model=SavedPlanOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("plans-write", limit=120, window_seconds=3600))],
)
async def save_plan(payload: SavePlanRequest, farmer: CurrentFarmerDep, session: SessionDep) -> SavedPlanOut:
    count = await session.scalar(select(func.count()).select_from(SavedPlan).where(SavedPlan.farmer_id == farmer.id))
    if (count or 0) >= MAX_PLANS_PER_FARMER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"You have reached the limit of {MAX_PLANS_PER_FARMER} saved plans. Delete one before saving another."
            ),
        )
    row = SavedPlan(
        farmer_id=farmer.id,
        crop=payload.recommendation.crop,
        suitability=payload.recommendation.suitability,
        expected_profit=payload.recommendation.expected_profit,
        location=payload.farm.location,
        season=payload.farm.season,
        note=payload.note,
        farm_snapshot=payload.farm.model_dump(),
        recommendation=payload.recommendation.model_dump(),
        weather=payload.weather,
        soil=payload.soil,
        market=payload.market,
        ai_explanation=payload.ai_explanation,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _plan_out(row)


@router.get("/plans", response_model=PlanPage)
async def list_plans(
    farmer: CurrentFarmerDep,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PlanPage:
    total = await session.scalar(select(func.count()).select_from(SavedPlan).where(SavedPlan.farmer_id == farmer.id))
    rows = (
        await session.scalars(
            select(SavedPlan)
            .where(SavedPlan.farmer_id == farmer.id)
            .order_by(SavedPlan.created_at.desc(), SavedPlan.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    items = [
        SavedPlanSummary(
            id=row.id,
            crop=row.crop,
            suitability=row.suitability,
            expected_profit=row.expected_profit,
            location=row.location,
            season=row.season,
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return PlanPage(items=items, total=total or 0, limit=limit, offset=offset)


@router.get("/plans/{plan_id}", response_model=SavedPlanOut)
async def get_plan(plan_id: uuid.UUID, farmer: CurrentFarmerDep, session: SessionDep) -> SavedPlanOut:
    row = await session.scalar(select(SavedPlan).where(SavedPlan.id == plan_id, SavedPlan.farmer_id == farmer.id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved plan not found")
    return _plan_out(row)


@router.delete("/plans/{plan_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: uuid.UUID, farmer: CurrentFarmerDep, session: SessionDep) -> None:
    result = await session.execute(delete(SavedPlan).where(SavedPlan.id == plan_id, SavedPlan.farmer_id == farmer.id))
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved plan not found")


@router.post(
    "/finance/plans",
    response_model=FinancePlanOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("finance-write", limit=120, window_seconds=3600))],
)
async def save_finance_plan(
    payload: SaveFinancePlanRequest, farmer: CurrentFarmerDep, session: SessionDep
) -> FinancePlanOut:
    if payload.saved_plan_id is not None:
        owns = await session.scalar(
            select(SavedPlan.id).where(SavedPlan.id == payload.saved_plan_id, SavedPlan.farmer_id == farmer.id)
        )
        if owns is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved plan not found")

    crop = str(payload.plan.get("crop") or "")
    if not crop:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Finance plan is missing its crop")

    # One live budget per crop per farmer: re-running the planner updates, never duplicates.
    row = await session.scalar(
        select(SeasonFinancePlan).where(SeasonFinancePlan.farmer_id == farmer.id, SeasonFinancePlan.crop == crop)
    )
    if row is None:
        row = SeasonFinancePlan(farmer_id=farmer.id, crop=crop)
        session.add(row)
    row.planning_source = str(payload.plan.get("planning_source") or "unknown")
    row.market_price_per_quintal = payload.market_price_per_quintal
    row.farm_snapshot = payload.farm.model_dump()
    row.actual_expenses = payload.actual_expenses
    row.plan = payload.plan
    row.saved_plan_id = payload.saved_plan_id
    await session.commit()
    await session.refresh(row)
    return _finance_out(row)


@router.get("/finance/plans", response_model=list[FinancePlanOut])
async def list_finance_plans(farmer: CurrentFarmerDep, session: SessionDep) -> list[FinancePlanOut]:
    rows = (
        await session.scalars(
            select(SeasonFinancePlan)
            .where(SeasonFinancePlan.farmer_id == farmer.id)
            .order_by(SeasonFinancePlan.updated_at.desc())
        )
    ).all()
    return [_finance_out(row) for row in rows]


@router.delete("/finance/plans/{plan_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_finance_plan(plan_id: uuid.UUID, farmer: CurrentFarmerDep, session: SessionDep) -> None:
    result = await session.execute(
        delete(SeasonFinancePlan).where(SeasonFinancePlan.id == plan_id, SeasonFinancePlan.farmer_id == farmer.id)
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finance plan not found")


@router.put("/profiles", response_model=ProfileOut, status_code=status.HTTP_200_OK)
async def upsert_profile(payload: ProfileRequest, farmer: CurrentFarmerDep, session: SessionDep) -> ProfileOut:
    """Create or replace a named farm profile, so field conditions survive a browser change."""
    row = await session.scalar(
        select(FarmProfileRecord).where(
            FarmProfileRecord.farmer_id == farmer.id, FarmProfileRecord.label == payload.label
        )
    )
    if row is None:
        count = await session.scalar(
            select(func.count()).select_from(FarmProfileRecord).where(FarmProfileRecord.farmer_id == farmer.id)
        )
        if (count or 0) >= MAX_PROFILES_PER_FARMER:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You have reached the limit of {MAX_PROFILES_PER_FARMER} saved farm profiles.",
            )
        row = FarmProfileRecord(farmer_id=farmer.id, label=payload.label)
        session.add(row)
    for field, value in payload.farm.model_dump().items():
        setattr(row, field, value)
    row.is_default = payload.is_default
    if payload.is_default:
        await session.flush()
        for other in await session.scalars(
            select(FarmProfileRecord).where(FarmProfileRecord.farmer_id == farmer.id, FarmProfileRecord.id != row.id)
        ):
            other.is_default = False
    await session.commit()
    await session.refresh(row)
    return _profile_out(row)


@router.get("/profiles", response_model=list[ProfileOut])
async def list_profiles(farmer: CurrentFarmerDep, session: SessionDep) -> list[ProfileOut]:
    rows = (
        await session.scalars(
            select(FarmProfileRecord)
            .where(FarmProfileRecord.farmer_id == farmer.id)
            .order_by(FarmProfileRecord.is_default.desc(), FarmProfileRecord.updated_at.desc())
        )
    ).all()
    return [_profile_out(row) for row in rows]


@router.delete("/profiles/{profile_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: uuid.UUID, farmer: CurrentFarmerDep, session: SessionDep) -> None:
    result = await session.execute(
        delete(FarmProfileRecord).where(FarmProfileRecord.id == profile_id, FarmProfileRecord.farmer_id == farmer.id)
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm profile not found")
