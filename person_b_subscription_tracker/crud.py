"""CRUD + query layer for Person B. Routers never touch the ORM directly."""
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Subscription
from services.cost_calculator import normalize_tags


def get_subscription(db: Session, subscription_id: int) -> Optional[Subscription]:
    return db.get(Subscription, subscription_id)


def create_subscription(db: Session, **fields) -> Subscription:
    if fields.get("tags") is not None:
        fields["tags_csv"] = normalize_tags(fields.pop("tags"))
    subscription = Subscription(**fields)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def update_subscription(db: Session, subscription: Subscription, changes: dict) -> Subscription:
    if "tags" in changes and changes["tags"] is not None:
        changes["tags_csv"] = normalize_tags(changes.pop("tags"))
    for field, value in changes.items():
        if value is not None:
            setattr(subscription, field, value)
    db.commit()
    db.refresh(subscription)
    return subscription


def delete_subscription(db: Session, subscription: Subscription) -> None:
    db.delete(subscription)
    db.commit()


def list_subscriptions(
    db: Session,
    *,
    active: Optional[bool] = None,
    category: Optional[str] = None,
    frequency: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Subscription]:
    stmt = select(Subscription)
    if active is not None:
        stmt = stmt.where(Subscription.active == active)
    if category:
        stmt = stmt.where(func.lower(Subscription.category) == category.lower())
    if frequency:
        stmt = stmt.where(Subscription.billing_frequency == frequency)
    stmt = stmt.order_by(Subscription.next_renewal_date.asc(), Subscription.id.asc())
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def renewals_within(db: Session, days: int, *, include_overdue: bool = True) -> list[Subscription]:
    """Active subscriptions renewing within the next `days` days (optionally overdue)."""
    today = date.today()
    horizon = date.fromordinal(today.toordinal() + days)
    stmt = select(Subscription).where(Subscription.active.is_(True))
    if include_overdue:
        stmt = stmt.where(Subscription.next_renewal_date <= horizon)
    else:
        stmt = stmt.where(Subscription.next_renewal_date.between(today, horizon))
    stmt = stmt.order_by(Subscription.next_renewal_date.asc())
    return list(db.scalars(stmt).all())


def all_active(db: Session) -> list[Subscription]:
    return list(db.scalars(select(Subscription).where(Subscription.active.is_(True))).all())


def counts(db: Session) -> tuple[int, int]:
    active = db.scalar(select(func.count(Subscription.id)).where(Subscription.active.is_(True))) or 0
    inactive = db.scalar(select(func.count(Subscription.id)).where(Subscription.active.is_(False))) or 0
    return int(active), int(inactive)


def distinct_tags(db: Session) -> list[tuple[str, int]]:
    """Tag -> subscription count (tags are stored comma-separated in tags_csv)."""
    tags: dict[str, int] = {}
    for (raw,) in db.execute(select(Subscription.tags_csv)).all():
        for tag in (raw or "").split(","):
            tag = tag.strip()
            if tag:
                tags[tag] = tags.get(tag, 0) + 1
    return sorted(tags.items(), key=lambda item: (-item[1], item[0]))
