# Subscription Renewal & Cost Tracker (Person B)

CSI3007 - Advanced Python Programming | Person B: **Shravan N A (23MID0445)**

A subscription manager that answers two questions every month: **"what do I
pay for?"** and **"what's renewing soon?"** It normalizes costs across
weekly / monthly / quarterly / yearly billing, forecasts renewals with
urgency levels, and exposes a **stable export contract** that Person A
consumes over HTTP REST.

```
   Person B (this app) ──GET /integration/export──► Person A
   (source of truth for subscriptions)              imports as expenses
```

## Features

- **Subscriptions CRUD**: name, category, plan, amount-per-period, currency,
  billing frequency (`weekly|monthly|quarterly|yearly`), next renewal date,
  payment method, tags, active flag, notes.
- **Cost normalization**: every subscription exposes `monthly_cost` and
  `yearly_cost` computed from a single source of truth
  (weekly = amount x 52/12, quarterly = /3, yearly = /12) - the UI, `/total`
  and the export payload can never disagree.
- **Renewal forecast**: `GET /renewals?days=30` returns active subscriptions
  due in the window, soonest first, with `days_until_renewal` and urgency
  (`overdue | this_week | soon | later`). Overdue items included by default.
- **Totals**: `GET /total` - monthly/yearly totals per currency, plus
  breakdowns by category and frequency (active subscriptions only).
- **Category & tag exploration**: case-insensitive category drill-down
  (unknown category = valid empty result) and distinct-tag counts.
- **Integration export**: `GET /integration/export` - a versioned, stable
  JSON contract (`contract_version: 1.0`) with a permanent `external_ref`
  (`B-SUB-<id>`) per subscription and pre-normalized `monthly_cost`, so
  Person A can import idempotently without ever touching this app's DB file.
- **Streamlit dashboard**: spend donut, totals KPIs, 7-day renewal preview,
  subscription table with "mark renewed" (advances the date by the billing
  frequency), renewal forecast with look-ahead slider, tag explorer, and a
  live view of the export contract.

## Tech stack

| Layer     | Technology |
|-----------|------------|
| Backend   | Python 3.12, FastAPI, Pydantic v2 |
| Database  | SQLite via SQLAlchemy 2 (own file: `data/subscriptions.db`) |
| Frontend  | Streamlit + Plotly (pure REST client) |
| Testing   | pytest + FastAPI TestClient (10 tests) |
| Deploy    | Render (see `RENDER_DEPLOYMENT.md`) |

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                 # placeholders only
python seed_data.py                  # 10 demo subscriptions (idempotent)

uvicorn main:app --host 127.0.0.1 --port 8002 --reload   # terminal 1
streamlit run app.py                                      # terminal 2

python -m pytest -q
```

Interactive API docs: <http://127.0.0.1:8002/docs>

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/subscriptions.db` | Own SQLite file (never shared) |
| `APP_PORT` | `8002` | Backend port |
| `API_BASE_URL` (frontend) | `http://127.0.0.1:8002` | Where Streamlit finds the API |

## API summary

Full reference with examples: `API_DOCUMENTATION.md`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + DB probe |
| GET/POST | `/subscriptions` | List (filterable) / create |
| GET/PUT/DELETE | `/subscriptions/{id}` | Read / partial update / delete |
| GET | `/renewals?days=30` | Renewal forecast + urgency |
| GET | `/total` | Monthly/yearly totals + breakdowns |
| GET | `/category/{name}` | Category drill-down (valid-empty semantics) |
| GET | `/tags` | Distinct tags with counts |
| GET | `/integration/export` | **Stable contract consumed by Person A** |

## Project structure

```
person_b_subscription_tracker/
├── main.py                    # FastAPI app + lifespan
├── config.py                  # 12-factor env-var settings
├── database.py                # SQLAlchemy engine/session (own SQLite file)
├── models.py                  # Subscription ORM model (+ computed properties)
├── schemas.py                 # Pydantic v2 contracts
├── crud.py                    # All DB access
├── routers/
│   ├── subscriptions.py       # CRUD + /renewals /total /category /tags
│   └── integration.py         # /integration/export (stable contract)
├── services/
│   └── cost_calculator.py     # Frequency normalization + renewal advance + tags
├── app.py                     # Streamlit frontend (REST client)
├── ui_common.py               # HTTP helpers for the frontend
├── seed_data.py               # 10 demo subscriptions (idempotent)
├── tests/                     # pytest suite
├── .env.example               # Placeholders ONLY
└── requirements.txt
```

## Integration contract (what B exposes to A)

`GET /integration/export` (frozen fields, additive changes bump
`contract_version`):

```json
{
  "service": "subscription-cost-tracker",
  "contract_version": "1.0",
  "generated_at": "2026-10-28T13:34:56Z",
  "count": 2,
  "subscriptions": [
    {"external_ref": "B-SUB-1", "name": "Netflix", "category": "Streaming",
     "plan": "Premium 4K", "tags": ["family", "ott"], "billing_frequency": "monthly",
     "amount": 649.0, "monthly_cost": 649.0, "currency": "INR",
     "active": true, "next_renewal_date": "2026-11-09"}
  ]
}
```

Rules: `external_ref` is permanent (`B-SUB-<id>`); `monthly_cost` is
pre-normalized so consumers never re-implement frequency math; inactive
subscriptions are included with `active: false` - the consumer decides.

## Known limitations & unverified items

- Sample prices in `seed_data.py` are illustrative, not current vendor prices.
- Totals group by currency, but there is no FX conversion between currencies.
- "Mark renewed" advances by one period from today (clamped to month length);
  no partial-period proration.

## Git quickstart (GitHub-ready)

```bash
git init
git add .
git commit -m "CSI3007 Person B: subscription renewal & cost tracker"
git branch -M main
git remote add origin https://github.com/<your-user>/csi3007-subscription-cost-tracker.git
git push -u origin main
```
