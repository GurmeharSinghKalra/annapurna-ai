"""Server-side records for farmer accounts, saved plans, and cached market data.

Everything a farmer creates is owned by exactly one ``Farmer`` row and is deleted with that
farmer, so "delete my account" is a single statement rather than a manual sweep.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# JSONB on Postgres (indexable, binary) and plain JSON on SQLite, from one column definition.
JSONColumn = JSON().with_variant(JSONB, "postgresql")


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class Farmer(TimestampMixin, Base):
    """An account. Phone is the login identifier; email is optional and only used for recovery."""

    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="English", nullable=False)
    location: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profiles: Mapped[list[FarmProfileRecord]] = relationship(
        back_populates="farmer", cascade="all, delete-orphan", passive_deletes=True
    )
    plans: Mapped[list[SavedPlan]] = relationship(
        back_populates="farmer", cascade="all, delete-orphan", passive_deletes=True
    )
    finance_plans: Mapped[list[SeasonFinancePlan]] = relationship(
        back_populates="farmer", cascade="all, delete-orphan", passive_deletes=True
    )
    sessions: Mapped[list[RefreshSession]] = relationship(
        back_populates="farmer", cascade="all, delete-orphan", passive_deletes=True
    )


class FarmProfileRecord(TimestampMixin, Base):
    """A named set of field conditions the farmer reuses between seasons."""

    __tablename__ = "farm_profiles"
    __table_args__ = (
        UniqueConstraint("farmer_id", "label", name="uq_farm_profile_label_per_farmer"),
        Index("ix_farm_profiles_farmer_default", "farmer_id", "is_default"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    farmer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    land_size: Mapped[float] = mapped_column(Float, nullable=False)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_crop: Mapped[str] = mapped_column(String(40), nullable=False)
    soil_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    nitrogen: Mapped[float] = mapped_column(Float, nullable=False)
    phosphorus: Mapped[float] = mapped_column(Float, nullable=False)
    potassium: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall: Mapped[float] = mapped_column(Float, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    market_priority: Mapped[str] = mapped_column(String(30), nullable=False)

    farmer: Mapped[Farmer] = relationship(back_populates="profiles")


class SavedPlan(TimestampMixin, Base):
    """A recommendation snapshot the farmer kept, with the context that produced it."""

    __tablename__ = "saved_plans"
    __table_args__ = (Index("ix_saved_plans_farmer_created", "farmer_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop: Mapped[str] = mapped_column(String(50), nullable=False)
    suitability: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_profit: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(String(280), nullable=True)

    # Snapshots, not live joins: a saved plan must still read correctly after the crop
    # table, the price feed, or the scoring weights change.
    farm_snapshot: Mapped[dict] = mapped_column(JSONColumn, nullable=False)
    recommendation: Mapped[dict] = mapped_column(JSONColumn, nullable=False)
    weather: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    soil: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    market: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    ai_explanation: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)

    farmer: Mapped[Farmer] = relationship(back_populates="plans")
    finance_plans: Mapped[list[SeasonFinancePlan]] = relationship(
        back_populates="saved_plan", cascade="all, delete-orphan", passive_deletes=True
    )


class SeasonFinancePlan(TimestampMixin, Base):
    """A season budget: tracked expenses plus the computed plan they produced."""

    __tablename__ = "season_finance_plans"
    __table_args__ = (Index("ix_finance_plans_farmer_created", "farmer_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    saved_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("saved_plans.id", ondelete="CASCADE"), index=True, nullable=True
    )
    crop: Mapped[str] = mapped_column(String(50), nullable=False)
    planning_source: Mapped[str] = mapped_column(String(160), nullable=False)
    market_price_per_quintal: Mapped[int | None] = mapped_column(Integer, nullable=True)

    farm_snapshot: Mapped[dict] = mapped_column(JSONColumn, nullable=False)
    actual_expenses: Mapped[dict] = mapped_column(JSONColumn, default=dict, nullable=False)
    plan: Mapped[dict] = mapped_column(JSONColumn, nullable=False)

    farmer: Mapped[Farmer] = relationship(back_populates="finance_plans")
    saved_plan: Mapped[SavedPlan | None] = relationship(back_populates="finance_plans")


class RefreshSession(Base):
    """One long-lived login. Storing a hash means a database leak cannot replay the token."""

    __tablename__ = "refresh_sessions"
    __table_args__ = (Index("ix_refresh_sessions_farmer_expires", "farmer_id", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("farmers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    farmer: Mapped[Farmer] = relationship(back_populates="sessions")

    @property
    def is_usable(self) -> bool:
        if self.revoked_at is not None:
            return False
        expires_at = self.expires_at
        if expires_at.tzinfo is None:  # SQLite returns naive datetimes.
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at > _now()


class MarketPriceSnapshot(TimestampMixin, Base):
    """Cached upstream mandi price.

    The mandi feed publishes once a day and rate-limits callers, so every farmer in a district
    asking for the same commodity must not become a separate upstream request. This row is also
    what lets the API answer with a dated price when the feed is briefly unreachable.
    """

    __tablename__ = "market_price_snapshots"
    __table_args__ = (
        UniqueConstraint("commodity", "state", "district", name="uq_market_snapshot_scope"),
        Index("ix_market_snapshot_fetched", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    commodity: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    district: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    market: Mapped[str | None] = mapped_column(String(120), nullable=True)
    variety: Mapped[str | None] = mapped_column(String(120), nullable=True)
    modal_price_per_quintal: Mapped[int] = mapped_column(Integer, nullable=False)
    min_price_per_quintal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_price_per_quintal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arrival_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)


class MarketPriceHistory(Base):
    """Append-only daily price points, so "trend" can be measured instead of hardcoded."""

    __tablename__ = "market_price_history"
    __table_args__ = (
        UniqueConstraint("commodity", "state", "district", "arrival_date", name="uq_market_history_point"),
        Index("ix_market_history_scope_observed", "commodity", "state", "district", "observed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    commodity: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    district: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    arrival_date: Mapped[str] = mapped_column(String(40), nullable=False)
    modal_price_per_quintal: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
