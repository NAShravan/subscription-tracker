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


def charges_in_month(
    next_renewal: date, frequency: str, month: str, *, not_before: Union[date, None] = None
) -> list[date]:
    """Billing dates falling inside `month` ("YYYY-MM"), projected from the
    subscription's next renewal date by stepping whole billing periods
    forwards (future months) or backwards (past months).

    Backward projection assumes the plan was billed continuously; dates
    before `not_before` (e.g. the day the subscription was recorded) are
    dropped. Monthly/quarterly/yearly steps are anchored on next_renewal so
    month-end clamping (Jan 31 -> Feb 28) does not drift.
    """
    if frequency not in FREQUENCY_TO_MONTHLY:
        raise ValueError(f"Unknown billing frequency: {frequency!r}")
    year, mon = (int(part) for part in month.split("-"))
    start = date(year, mon, 1)
    end = _add_months(start, 1)  # exclusive

    def nth(n: int) -> date:
        if frequency == "weekly":
            return date.fromordinal(next_renewal.toordinal() + 7 * n)
        step = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
        return _add_months(next_renewal, step * n)

    # Jump close to the target month, then walk.
    if frequency == "weekly":
        n = (start.toordinal() - next_renewal.toordinal()) // 7 - 1
    else:
        step = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
        months_apart = (start.year - next_renewal.year) * 12 + (start.month - next_renewal.month)
        n = months_apart // step - 1
    dates = []
    while True:
        when = nth(n)
        if when >= end:
            break
        if when >= start and (not_before is None or when >= not_before):
            dates.append(when)
        n += 1
    return dates


def normalize_tags(tags) -> str:
    """Lowercase, dedupe (stable order), join with commas for storage."""
    seen: list[str] = []
    for tag in tags or []:
        cleaned = str(tag).strip().lower()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return ",".join(seen)
