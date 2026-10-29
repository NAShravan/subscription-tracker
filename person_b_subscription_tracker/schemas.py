"""Pydantic v2 schemas defining the public JSON contract of Person B's API."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

BillingFrequency = Literal["weekly", "monthly", "quarterly", "yearly"]


# ------------------------------------------------------------ subscriptions
class SubscriptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    plan: Optional[str] = Field(default=None, max_length=120)
    amount: float = Field(gt=0, description="Price per billing period")
    currency: str = Field(default="INR", min_length=1, max_length=8)
    billing_frequency: BillingFrequency
    next_renewal_date: date
    payment_method: Optional[str] = Field(default=None, max_length=60)
    tags: list[str] = Field(default_factory=list, max_length=20)
    active: bool = True
    notes: Optional[str] = Field(default=None, max_length=500)


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    category: Optional[str] = Field(default=None, min_length=1, max_length=60)
    plan: Optional[str] = Field(default=None, max_length=120)
    amount: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, min_length=1, max_length=8)
    billing_frequency: Optional[BillingFrequency] = None
    next_renewal_date: Optional[date] = None
    payment_method: Optional[str] = Field(default=None, max_length=60)
    tags: Optional[list[str]] = Field(default=None, max_length=20)
    active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    plan: str
    amount: float
    currency: str
    billing_frequency: BillingFrequency
    next_renewal_date: date
    payment_method: str
    tags: list[str]
    active: bool
    notes: str
    monthly_cost: float
    yearly_cost: float
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------- renewals
class RenewalOut(SubscriptionOut):
    days_until_renewal: int
    urgency: Literal["overdue", "this_week", "soon", "later"]


# ------------------------------------------------------------------ totals
class CurrencyTotals(BaseModel):
    currency: str
    monthly_total: float
    yearly_total: float


class CategoryTotals(BaseModel):
    currency: str
    category: str
    count: int
    monthly_total: float


class FrequencyTotals(BaseModel):
    currency: str
    billing_frequency: BillingFrequency
    count: int
    monthly_total: float


class MonthCharge(BaseModel):
    subscription_id: int
    name: str
    category: str
    billing_frequency: BillingFrequency
    charge_date: date
    amount: float
    currency: str


class MonthDueTotals(BaseModel):
    currency: str
    count: int
    total: float


class TotalsOut(BaseModel):
    active_count: int
    inactive_count: int
    # Billing-cycle-normalized run rate of ACTIVE subscriptions (independent of month).
    currencies: list[CurrencyTotals]
    by_category: list[CategoryTotals]
    by_frequency: list[FrequencyTotals]
    # Only when ?month=YYYY-MM is given: actual charges projected to fall due
    # in that calendar month (a yearly plan is 0 in most months and its full
    # price in its renewal month).
    month: Optional[str] = None
    due_in_month: Optional[list[MonthCharge]] = None
    due_in_month_totals: Optional[list[MonthDueTotals]] = None


class CategoryDetail(BaseModel):
    category: str
    count: int
    monthly_total: float
    subscriptions: list[SubscriptionOut]


class TagOut(BaseModel):
    tag: str
    count: int


# ----------------------------------------------------------------- export
class ExportSubscription(BaseModel):
    external_ref: str
    name: str
    category: str
    plan: str
    tags: list[str]
    billing_frequency: BillingFrequency
    amount: float
    monthly_cost: float
    currency: str
    active: bool
    next_renewal_date: date


class ExportPayload(BaseModel):
    service: str
    contract_version: str
    generated_at: str
    count: int
    subscriptions: list[ExportSubscription]
