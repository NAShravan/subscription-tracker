"""Tests for GET /total?month=YYYY-MM, filter validation and renewal projection."""
from datetime import date

from services.cost_calculator import charges_in_month


def test_charges_in_month_monthly_and_month_end_clamp():
    # Anchored on the 31st: Feb clamps to 28, March returns to 31 (no drift).
    assert charges_in_month(date(2026, 1, 31), "monthly", "2026-02") == [date(2026, 2, 28)]
    assert charges_in_month(date(2026, 1, 31), "monthly", "2026-03") == [date(2026, 3, 31)]
    # Backwards projection into an earlier month.
    assert charges_in_month(date(2026, 5, 10), "monthly", "2026-02") == [date(2026, 2, 10)]


def test_charges_in_month_yearly_quarterly_weekly():
    assert charges_in_month(date(2026, 7, 1), "yearly", "2026-07") == [date(2026, 7, 1)]
    assert charges_in_month(date(2026, 7, 1), "yearly", "2026-08") == []
    assert charges_in_month(date(2026, 7, 1), "yearly", "2027-07") == [date(2027, 7, 1)]
    assert charges_in_month(date(2026, 1, 15), "quarterly", "2026-04") == [date(2026, 4, 15)]
    assert charges_in_month(date(2026, 1, 15), "quarterly", "2026-05") == []
    weekly = charges_in_month(date(2026, 6, 1), "weekly", "2026-06")
    assert weekly == [date(2026, 6, d) for d in (1, 8, 15, 22, 29)]


def test_charges_in_month_respects_not_before():
    assert charges_in_month(date(2026, 5, 10), "monthly", "2026-02", not_before=date(2026, 4, 1)) == []


def _create(client, **overrides):
    body = {"name": "Plan", "category": "MonthTest", "amount": 100.0, "billing_frequency": "monthly",
            "next_renewal_date": "2030-03-10"}
    body.update(overrides)
    response = client.post("/subscriptions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_total_with_month_lists_projected_charges(client):
    monthly = _create(client, name="MonthTest Monthly", amount=100.0)
    yearly = _create(client, name="MonthTest Yearly", amount=1200.0, billing_frequency="yearly",
                     next_renewal_date="2030-03-20")
    body = client.get("/total", params={"month": "2030-03"}).json()
    assert body["month"] == "2030-03"
    ours = [c for c in body["due_in_month"] if c["subscription_id"] in {monthly["id"], yearly["id"]}]
    assert [(c["name"], c["charge_date"], c["amount"]) for c in ours] == [
        ("MonthTest Monthly", "2030-03-10", 100.0),
        ("MonthTest Yearly", "2030-03-20", 1200.0),
    ]
    april = client.get("/total", params={"month": "2030-04"}).json()
    ours = [c for c in april["due_in_month"] if c["subscription_id"] in {monthly["id"], yearly["id"]}]
    assert [c["name"] for c in ours] == ["MonthTest Monthly"]  # yearly plan not due in April
    # Normalized run-rate fields are unchanged by the month parameter.
    assert april["currencies"] == body["currencies"]


def test_total_without_month_keeps_v1_shape(client):
    body = client.get("/total").json()
    assert body["month"] is None and body["due_in_month"] is None
    assert {"active_count", "inactive_count", "currencies", "by_category", "by_frequency"} <= set(body)


def test_total_rejects_bad_month(client):
    for bad in ("2026-13", "2026-5", "May"):
        assert client.get("/total", params={"month": bad}).status_code == 422


def test_inactive_subscriptions_are_not_due(client):
    sub = _create(client, name="MonthTest Paused", active=False, next_renewal_date="2031-01-05")
    body = client.get("/total", params={"month": "2031-01"}).json()
    assert sub["id"] not in {c["subscription_id"] for c in body["due_in_month"]}


def test_frequency_filter_is_validated(client):
    assert client.get("/subscriptions", params={"frequency": "daily"}).status_code == 422
    assert client.get("/subscriptions", params={"frequency": "yearly"}).status_code == 200


def test_missing_subscription_is_404(client):
    assert client.get("/subscriptions/999999").status_code == 404
    assert client.put("/subscriptions/999999", json={"amount": 5}).status_code == 404
    assert client.delete("/subscriptions/999999").status_code == 404


def test_export_contract_reflects_new_subscription(client):
    sub = _create(client, name="Export Probe", amount=12000.0, billing_frequency="yearly",
                  next_renewal_date=date.today().isoformat())
    payload = client.get("/integration/export").json()
    entry = next(s for s in payload["subscriptions"] if s["external_ref"] == f"B-SUB-{sub['id']}")
    assert entry["monthly_cost"] == 1000.0 and entry["currency"] == "INR" and entry["active"] is True
