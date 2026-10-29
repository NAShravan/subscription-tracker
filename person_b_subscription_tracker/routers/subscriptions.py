"""Subscription CRUD + analytics endpoints for Person B."""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from crud import (
    all_active,
    counts,
    create_subscription,
    delete_subscription,
    distinct_tags,
    get_subscription,
    list_subscriptions,
    renewals_within,
    update_subscription,
)
from database import get_db
from services.cost_calculator import charges_in_month
from schemas import (
    CategoryDetail,
    CategoryTotals,
    CurrencyTotals,
    FrequencyTotals,
    MonthCharge,
    MonthDueTotals,
    RenewalOut,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionUpdate,
    TagOut,
    TotalsOut,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
analytics = APIRouter(tags=["Analytics"])


def _urgency(days_until: int) -> str:
    if days_until < 0:
        return "overdue"
    if days_until <= 7:
        return "this_week"
    if days_until <= 30:
        return "soon"
    return "later"


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription_endpoint(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    """Register a subscription (amount is per billing period)."""
    return create_subscription(db, **payload.model_dump())


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions_endpoint(
    active: Optional[bool] = Query(default=None),
    category: Optional[str] = Query(default=None, max_length=60),
    frequency: Optional[Literal["weekly", "monthly", "quarterly", "yearly"]] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List subscriptions, soonest renewal first."""
    return list_subscriptions(db, active=active, category=category, frequency=frequency, limit=limit, offset=offset)


@router.get("/{subscription_id}", response_model=SubscriptionOut)
def get_subscription_endpoint(subscription_id: int, db: Session = Depends(get_db)):
    subscription = get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Subscription {subscription_id} not found")
    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription_endpoint(
    subscription_id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db)
):
    """Partial update - e.g. mark renewed by advancing next_renewal_date."""
    subscription = get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Subscription {subscription_id} not found")
    return update_subscription(db, subscription, payload.model_dump(exclude_unset=True))


@router.delete("/{subscription_id}")
def delete_subscription_endpoint(subscription_id: int, db: Session = Depends(get_db)):
    subscription = get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Subscription {subscription_id} not found")
    delete_subscription(db, subscription)
    return {"deleted": True, "id": subscription_id}


# ------------------------------------------------------------------ analytics
@analytics.get("/renewals", response_model=list[RenewalOut])
def renewals_endpoint(
    days: int = Query(default=30, ge=1, le=365),
    include_overdue: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """Active subscriptions due within `days` days, soonest first."""
    today = date.today()
    result: list[RenewalOut] = []
    for subscription in renewals_within(db, days, include_overdue=include_overdue):
        item = SubscriptionOut.model_validate(subscription).model_dump()
        days_until = (subscription.next_renewal_date - today).days
        result.append(RenewalOut(**item, days_until_renewal=days_until, urgency=_urgency(days_until)))
    return result


@analytics.get("/total", response_model=TotalsOut)
def totals_endpoint(
    month: Optional[str] = Query(
        default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Optional YYYY-MM: also list the charges projected to fall due in that month",
    ),
    db: Session = Depends(get_db),
):
    """Monthly / yearly cost totals across active subscriptions, split by currency.

    With `month`, the response also carries `due_in_month`: the renewals of
    active subscriptions projected into that calendar month from each
    next_renewal_date and billing frequency.
    """
    active, inactive = counts(db)
    currency_totals: dict[str, dict[str, float]] = {}
    by_category: dict[tuple[str, str], dict] = {}
    by_frequency: dict[tuple[str, str], dict] = {}
    for subscription in all_active(db):
        cur = subscription.currency
        bucket = currency_totals.setdefault(cur, {"monthly_total": 0.0, "yearly_total": 0.0})
        bucket["monthly_total"] += subscription.monthly_cost
        bucket["yearly_total"] += subscription.yearly_cost

        cat_key = (cur, subscription.category)
        entry = by_category.setdefault(cat_key, {"count": 0, "monthly_total": 0.0})
        entry["count"] += 1
        entry["monthly_total"] += subscription.monthly_cost

        freq_key = (cur, subscription.billing_frequency)
        entry = by_frequency.setdefault(freq_key, {"count": 0, "monthly_total": 0.0})
        entry["count"] += 1
        entry["monthly_total"] += subscription.monthly_cost

    due: Optional[list[MonthCharge]] = None
    due_totals: Optional[list[MonthDueTotals]] = None
    if month:
        due = []
        for subscription in all_active(db):
            for when in charges_in_month(
                subscription.next_renewal_date, subscription.billing_frequency, month,
                not_before=subscription.created_at.date() if subscription.created_at else None,
            ):
                due.append(MonthCharge(
                    subscription_id=subscription.id, name=subscription.name, category=subscription.category,
                    billing_frequency=subscription.billing_frequency, charge_date=when,
                    amount=round(subscription.amount, 2), currency=subscription.currency,
                ))
        due.sort(key=lambda charge: (charge.charge_date, charge.subscription_id))
        per_currency: dict[str, dict] = {}
        for charge in due:
            bucket = per_currency.setdefault(charge.currency, {"count": 0, "total": 0.0})
            bucket["count"] += 1
            bucket["total"] += charge.amount
        due_totals = [
            MonthDueTotals(currency=cur, count=v["count"], total=round(v["total"], 2))
            for cur, v in sorted(per_currency.items())
        ]

    return TotalsOut(
        active_count=active,
        inactive_count=inactive,
        month=month,
        due_in_month=due,
        due_in_month_totals=due_totals,
        currencies=[
            CurrencyTotals(currency=cur, monthly_total=round(v["monthly_total"], 2), yearly_total=round(v["yearly_total"], 2))
            for cur, v in sorted(currency_totals.items())
        ],
        by_category=[
            CategoryTotals(currency=cur, category=cat, count=v["count"], monthly_total=round(v["monthly_total"], 2))
            for (cur, cat), v in sorted(by_category.items(), key=lambda kv: (-kv[1]["monthly_total"], kv[0][1]))
        ],
        by_frequency=[
            FrequencyTotals(currency=cur, billing_frequency=freq, count=v["count"], monthly_total=round(v["monthly_total"], 2))
            for (cur, freq), v in sorted(by_frequency.items(), key=lambda kv: (kv[0][1],))
        ],
    )


@analytics.get("/category/{name}", response_model=CategoryDetail)
def category_detail_endpoint(name: str, db: Session = Depends(get_db)):
    """Subscriptions of one category (case-insensitive). Unknown-but-unused
    category names are a VALID empty result (zero count), not an error."""
    subscriptions = list_subscriptions(db, category=name, limit=500)
    monthly = round(sum(s.monthly_cost for s in subscriptions), 2)
    return CategoryDetail(
        category=name,
        count=len(subscriptions),
        monthly_total=monthly,
        subscriptions=subscriptions,
    )


@analytics.get("/tags", response_model=list[TagOut])
def tags_endpoint(db: Session = Depends(get_db)):
    """Distinct tags with subscription counts (all subscriptions, any state)."""
    return [TagOut(tag=tag, count=count) for tag, count in distinct_tags(db)]
