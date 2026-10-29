"""API tests for Person B: CRUD, frequency math, renewals, totals, category, tags, export."""
from datetime import date, timedelta

TODAY = date.today()
ISO = lambda offset: (TODAY + timedelta(days=offset)).isoformat()  # noqa: E731


def _create(client, **overrides):
    body = {
        "name": "Netflix",
        "category": "Streaming",
        "plan": "Premium 4K",
        "amount": 649.0,
        "currency": "INR",
        "billing_frequency": "monthly",
        "next_renewal_date": ISO(10),
        "payment_method": "UPI Autopay",
        "tags": ["Family", "OTT", "family"],
        "notes": "",
    }
    body.update(overrides)
    response = client.post("/subscriptions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "subscription-cost-tracker"
    assert body["database"] == "connected"


def test_create_and_frequency_normalization(client):
    netflix = _create(client)
    assert netflix["monthly_cost"] == 649.0
    assert netflix["yearly_cost"] == 7788.0
    assert netflix["tags"] == ["family", "ott"]  # lowercased + deduped

    yearly = _create(client, name="Adobe CC", category="Software", amount=12000.0, billing_frequency="yearly")
    assert yearly["monthly_cost"] == 1000.0
    assert yearly["yearly_cost"] == 12000.0

    quarterly = _create(client, name="Cult.fit", category="Fitness", amount=1500.0, billing_frequency="quarterly")
    assert quarterly["monthly_cost"] == 500.0

    weekly = _create(client, name="Milk Delivery", category="Other", amount=100.0, billing_frequency="weekly")
    assert weekly["monthly_cost"] == round(100.0 * 52 / 12, 2)  # 433.33


def test_create_rejects_bad_frequency_and_amount(client):
    assert client.post(
        "/subscriptions",
        json={"name": "X", "category": "Other", "amount": 10.0, "billing_frequency": "daily",
              "next_renewal_date": ISO(1)},
    ).status_code == 422
    assert client.post(
        "/subscriptions",
        json={"name": "X", "category": "Other", "amount": 0, "billing_frequency": "monthly",
              "next_renewal_date": ISO(1)},
    ).status_code == 422


def test_list_filters(client):
    _create(client, name="Spotify", category="Music", amount=119.0, billing_frequency="monthly")
    _create(client, name="Old App", category="Music", amount=99.0, active=False, billing_frequency="monthly")

    all_music = client.get("/subscriptions", params={"category": "music"}).json()  # case-insensitive
    assert len(all_music) == 2
    active_music = client.get("/subscriptions", params={"category": "Music", "active": "true"}).json()
    assert len(active_music) == 1
    assert active_music[0]["name"] == "Spotify"

    by_freq = client.get("/subscriptions", params={"frequency": "yearly"}).json()
    assert all(item["billing_frequency"] == "yearly" for item in by_freq)


def test_get_update_delete(client):
    created = _create(client, name="iCloud", amount=75.0)
    subscription_id = created["id"]

    fetched = client.get(f"/subscriptions/{subscription_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "iCloud"

    updated = client.put(
        f"/subscriptions/{subscription_id}",
        json={"amount": 149.0, "tags": ["storage", "family"]},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 149.0
    assert updated.json()["tags"] == ["storage", "family"]

    deleted = client.delete(f"/subscriptions/{subscription_id}")
    assert deleted.json() == {"deleted": True, "id": subscription_id}
    assert client.get(f"/subscriptions/{subscription_id}").status_code == 404
    assert client.delete(f"/subscriptions/{subscription_id}").status_code == 404


def test_renewals_window_and_urgency(client):
    _create(client, name="Soon", next_renewal_date=ISO(3))          # this_week
    _create(client, name="Later", next_renewal_date=ISO(20))        # soon
    _create(client, name="Overdue", next_renewal_date=ISO(-2))      # overdue
    _create(client, name="FarAway", next_renewal_date=ISO(120))     # out of window

    renewals = client.get("/renewals", params={"days": 30}).json()
    names = [item["name"] for item in renewals]
    assert {"Soon", "Later", "Overdue"} <= set(names)
    assert "FarAway" not in names

    by_name = {item["name"]: item for item in renewals}
    assert by_name["Soon"]["urgency"] == "this_week"
    assert by_name["Later"]["urgency"] == "soon"
    assert by_name["Overdue"]["urgency"] == "overdue"
    assert by_name["Overdue"]["days_until_renewal"] == -2

    # Renewals are sorted soonest first (overdue first).
    days_list = [item["days_until_renewal"] for item in renewals]
    assert days_list == sorted(days_list)

    no_overdue = client.get("/renewals", params={"days": 30, "include_overdue": "false"}).json()
    assert "Overdue" not in [item["name"] for item in no_overdue]


def test_totals_endpoint(client):
    _create(client, name="Netflix", amount=649.0, billing_frequency="monthly")
    _create(client, name="Adobe CC", category="Software", amount=12000.0, billing_frequency="yearly")
    _create(client, name="iCloud", category="Cloud", amount=75.0, billing_frequency="monthly")
    _create(client, name="Inactive", amount=500.0, active=False, billing_frequency="monthly")

    totals = client.get("/total").json()
    assert totals["active_count"] >= 3
    assert totals["inactive_count"] >= 1
    inr = next(c for c in totals["currencies"] if c["currency"] == "INR")
    assert inr["monthly_total"] >= 649.0 + 1000.0 + 75.0
    # "Cloud" is unique to this test -> exact monthly total for the category.
    categories = {row["category"]: row["monthly_total"] for row in totals["by_category"]}
    assert categories["Cloud"] == 75.0
    frequencies = {row["billing_frequency"]: row for row in totals["by_frequency"]}
    assert frequencies["yearly"]["count"] >= 1


def test_category_detail_valid_empty(client):
    body = client.get("/category/DoesNotExist").json()
    assert body["count"] == 0
    assert body["monthly_total"] == 0.0
    assert body["subscriptions"] == []


def test_tags_endpoint(client):
    _create(client, name="One", tags=["Family", "OTT"])
    _create(client, name="Two", tags=["family", "music"])
    tags = {item["tag"]: item["count"] for item in client.get("/tags").json()}
    # Self-contained assertions: this test itself contributes "family" x2,
    # "ott" x1 and "music" x1 (other tests may add more family/ott subs).
    assert tags["family"] >= 2
    assert tags["ott"] >= 1
    assert tags["music"] == 1


def test_integration_export_contract(client):
    created = _create(client, name="Netflix", amount=649.0, tags=["ott"])
    payload = client.get("/integration/export").json()

    # Contract keys (Person A relies on these exact names).
    assert {"service", "contract_version", "generated_at", "count", "subscriptions"} <= set(payload)
    assert payload["count"] == len(payload["subscriptions"]) >= 1

    entry = next(s for s in payload["subscriptions"] if s["external_ref"] == f"B-SUB-{created['id']}")
    assert entry["name"] == "Netflix"
    assert entry["monthly_cost"] == 649.0
    assert entry["currency"] == "INR"
    assert entry["active"] is True
    assert {"external_ref", "name", "category", "tags", "billing_frequency", "amount",
            "monthly_cost", "currency", "active", "next_renewal_date"} <= set(entry)
