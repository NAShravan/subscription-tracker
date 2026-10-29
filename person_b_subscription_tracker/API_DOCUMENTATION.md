# API Documentation - Person B (Subscription Renewal & Cost Tracker API)

- Base URL (local): `http://127.0.0.1:8002`
- Interactive OpenAPI docs: `http://127.0.0.1:8002/docs`
- Auth: none (course demo scope)
- Content type: `application/json`
- Errors: `422` validation (e.g. unknown billing frequency), `404` missing
  resource, `409` not used here, `500` never expected on documented paths.

---

## System

### `GET /health`
```json
{
  "status": "ok",
  "service": "subscription-cost-tracker",
  "owner": "Person B - Shravan N A (23MID0445)",
  "version": "1.0.0",
  "database": "connected",
  "time": "2026-10-28T13:34:56.525138+00:00"
}
```

## Subscriptions

A subscription = one recurring payment. `amount` is the price **per billing
period**; `monthly_cost` / `yearly_cost` are computed responses
(weekly x 52/12, monthly x 1, quarterly / 3, yearly / 12).

### `POST /subscriptions` -> 201
```bash
curl -X POST http://127.0.0.1:8002/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Netflix", "category": "Streaming", "plan": "Premium 4K",
    "amount": 649.0, "currency": "INR", "billing_frequency": "monthly",
    "next_renewal_date": "2026-11-09", "payment_method": "UPI Autopay",
    "tags": ["Family", "OTT"]
  }'
```

```json
{
  "id": 1, "name": "Netflix", "category": "Streaming", "plan": "Premium 4K",
  "amount": 649.0, "currency": "INR", "billing_frequency": "monthly",
  "next_renewal_date": "2026-11-09", "payment_method": "UPI Autopay",
  "tags": ["family", "ott"], "active": true, "notes": "",
  "monthly_cost": 649.0, "yearly_cost": 7788.0,
  "created_at": "...", "updated_at": "..."
}
```

Notes: tags are lowercased and de-duplicated on save; `billing_frequency`
must be `weekly|monthly|quarterly|yearly` (anything else -> 422);
`amount` must be > 0.

### `GET /subscriptions`
Query params: `active` (`true`/`false`), `category` (case-insensitive),
`frequency`, `limit` (default 100), `offset`. Ordered by next renewal
(soonest first).

### `GET /subscriptions/{id}` -> 200 | 404
### `PUT /subscriptions/{id}` -> 200
Partial update. Typical uses: mark renewed
(`{"next_renewal_date": "..."}`), pause/resume (`{"active": false}`),
change plan/amount.

### `DELETE /subscriptions/{id}` -> 200
```json
{ "deleted": true, "id": 3 }
```

## Analytics

### `GET /renewals?days=30&include_overdue=true`
Active subscriptions renewing within `days` (1-365), soonest first, each with
`days_until_renewal` and `urgency`:

| urgency | meaning |
|---|---|
| `overdue` | renewal date already passed |
| `this_week` | due within 7 days |
| `soon` | due within 30 days |
| `later` | beyond 30 days (window up to `days`) |

```json
[
  {"id": 8, "name": "Xbox Game Pass Ultimate", "days_until_renewal": -2,
   "urgency": "overdue", "monthly_cost": 549.0, "...": "..."}
]
```

### `GET /total` and `GET /total?month=YYYY-MM`
Monthly/yearly totals across **active** subscriptions, split per currency,
with category and frequency breakdowns. These are billing-cycle-normalized
run rates (weekly x 52/12, quarterly / 3, yearly / 12) and do not depend on
`month`.

With `?month=YYYY-MM` the response additionally contains `month`,
`due_in_month` (each charge projected to fall due in that calendar month from
`next_renewal_date` and the billing frequency, never before the date the
subscription was recorded) and `due_in_month_totals` per currency. A yearly
plan contributes its full price only in its renewal month. Invalid months
(`2026-13`, `2026-5`) return 422. Without `month` the three fields are `null`.

```json
"month": "2026-10",
"due_in_month": [{"subscription_id": 1, "name": "Netflix", "category": "Streaming",
  "billing_frequency": "monthly", "charge_date": "2026-11-01", "amount": 649.0, "currency": "INR"}],
"due_in_month_totals": [{"currency": "INR", "count": 1, "total": 649.0}]
```

Base response:

```json
{
  "active_count": 9, "inactive_count": 1,
  "currencies": [{"currency": "INR", "monthly_total": 6233.26, "yearly_total": 74799.0}],
  "by_category": [
    {"currency": "INR", "category": "Education", "count": 1, "monthly_total": 2916.67}
  ],
  "by_frequency": [
    {"currency": "INR", "billing_frequency": "yearly", "count": 4, "monthly_total": 4291.67}
  ]
}
```

### `GET /category/{name}`
Case-insensitive drill-down. Unknown-but-unused categories are a **valid
empty result** (count 0, empty list), not a 404 - the category namespace is
freeform.

```json
{"category": "Music", "count": 1, "monthly_total": 119.0, "subscriptions": [ /* ... */ ]}
```

### `GET /tags`
Distinct tags with subscription counts (all subscriptions, any state):

```json
[{"tag": "family", "count": 4}, {"tag": "ott", "count": 3}]
```

## Integration export (consumed by Person A)

### `GET /integration/export`
The stable, versioned contract. Fields are frozen; additive changes bump
`contract_version`. Every subscription carries a permanent `external_ref`
(`B-SUB-<id>`) and a pre-normalized `monthly_cost`. Inactive subscriptions
are included with `active: false` so the consumer decides.

```json
{
  "service": "subscription-cost-tracker",
  "contract_version": "1.0",
  "generated_at": "2026-10-28T13:34:56.873193+00:00",
  "count": 10,
  "subscriptions": [
    {"external_ref": "B-SUB-1", "name": "Netflix", "category": "Streaming",
     "plan": "Premium 4K", "tags": ["family", "ott", "4k"],
     "billing_frequency": "monthly", "amount": 649.0, "monthly_cost": 649.0,
     "currency": "INR", "active": true, "next_renewal_date": "2026-11-09"}
  ]
}
```

Verified live: Person A imported 9 active subscriptions from this endpoint
(yearly 12000 -> monthly 1000.00; yearly 35000 -> monthly 2916.67) and a
re-run imported 0 duplicates - see `docs/FINAL_VERIFICATION_REPORT.md`.
