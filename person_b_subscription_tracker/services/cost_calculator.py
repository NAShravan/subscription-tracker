"""Billing-frequency math for Person B.

Normalization is the single source of truth for "monthly cost", so the UI,
the /total endpoint and the /integration/export payload all agree.
"""
from datetime import date
from typing import Union

VALID_FREQUENCIES = ("weekly", "monthly", "quarterly", "yearly")

# Average weeks per month = 52/12 (keeps weekly plans comparable).
FREQUENCY_TO_MONTHLY = {
    "weekly": 52.0 / 12.0,
    "monthly": 1.0,
    "quarterly": 1.0 / 3.0,
    "yearly": 1.0 / 12.0,
}

FREQUENCY_TO_YEARLY = {
    "weekly": 52.0,
    "monthly": 12.0,
    "quarterly": 4.0,
    "yearly": 1.0,
}


def monthly_equivalent(amount: float, frequency: str) -> float:
    """Cost per month, rounded to paise."""
    if frequency not in FREQUENCY_TO_MONTHLY:
        raise ValueError(f"Unknown billing frequency: {frequency!r}")
    return round(float(amount) * FREQUENCY_TO_MONTHLY[frequency], 2)


def yearly_equivalent(amount: float, frequency: str) -> float:
    if frequency not in FREQUENCY_TO_YEARLY:
        raise ValueError(f"Unknown billing frequency: {frequency!r}")
    return round(float(amount) * FREQUENCY_TO_YEARLY[frequency], 2)


def _add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp the day to the last valid day of the target month.
    if month == 12:
        first_of_next = date(year + 1, 1, 1)
    else:
        first_of_next = date(year, month + 1, 1)
    days_in_month = first_of_next.toordinal() - date(year, month, 1).toordinal()
    return date(year, month, min(day.day, days_in_month))


def advance_renewal(from_date: Union[date, None], frequency: str, *, today: Union[date, None] = None) -> date:
    """Next renewal date after `from_date` (default: today) for a frequency."""
    base = from_date or today or date.today()
    if frequency == "weekly":
        return date.fromordinal(base.toordinal() + 7)
    if frequency == "monthly":
        return _add_months(base, 1)
    if frequency == "quarterly":
        return _add_months(base, 3)
    if frequency == "yearly":
        return _add_months(base, 12)
    raise ValueError(f"Unknown billing frequency: {frequency!r}")


def normalize_tags(tags) -> str:
    """Lowercase, dedupe (stable order), join with commas for storage."""
    seen: list[str] = []
    for tag in tags or []:
        cleaned = str(tag).strip().lower()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return ",".join(seen)
