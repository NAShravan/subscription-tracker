"""GET /integration/export - the stable HTTP contract Person A consumes.

Contract rules (frozen):
- stable field names and types; additive changes bump contract_version;
- every subscription carries a STABLE external_ref ("B-SUB-<id>") so the
  consumer can import idempotently;
- monthly_cost is pre-normalized (weekly -> 52/12 avg, quarterly /3, yearly /12);
- inactive subscriptions are included with active=false so consumers decide.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import settings
from crud import list_subscriptions
from database import get_db
from schemas import ExportPayload, ExportSubscription

router = APIRouter(prefix="/integration", tags=["Integration"])


@router.get("/export", response_model=ExportPayload)
def export_endpoint(db: Session = Depends(get_db)):
    subscriptions = list_subscriptions(db, limit=1000)
    return ExportPayload(
        service=settings.service_name,
        contract_version=settings.contract_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
        count=len(subscriptions),
        subscriptions=[
            ExportSubscription(
                external_ref=f"B-SUB-{item.id}",
                name=item.name,
                category=item.category,
                plan=item.plan,
                tags=item.tags,
                billing_frequency=item.billing_frequency,
                amount=item.amount,
                monthly_cost=item.monthly_cost,
                currency=item.currency,
                active=item.active,
                next_renewal_date=item.next_renewal_date,
            )
            for item in subscriptions
        ],
    )
