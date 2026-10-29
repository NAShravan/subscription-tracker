"""SQLAlchemy ORM models for Person B - Subscription Renewal & Cost Tracker."""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    # Freeform but conventionally one of: Streaming, Music, Software, Fitness,
    # News, Education, Cloud, Gaming, Other.
    category: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # price per billing period
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    # weekly | monthly | quarterly | yearly (validated at the API boundary)
    billing_frequency: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    next_renewal_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    # Comma-separated lowercase tags stored raw, e.g. "family,ott,4k";
    # the `tags` property below exposes the parsed list in the JSON contract.
    tags_csv: Mapped[str] = mapped_column("tags", String(255), default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    notes: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # ---- computed conveniences (exposed in the JSON contract) -------------
    @property
    def tags(self) -> list[str]:
        return [tag for tag in self.tags_csv.split(",") if tag]

    @property
    def monthly_cost(self) -> float:
        from services.cost_calculator import monthly_equivalent

        return monthly_equivalent(self.amount, self.billing_frequency)

    @property
    def yearly_cost(self) -> float:
        from services.cost_calculator import yearly_equivalent

        return yearly_equivalent(self.amount, self.billing_frequency)
