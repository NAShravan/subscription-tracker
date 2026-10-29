# Implementation Checklist - Person B (Subscription Tracker)

Status legend: `[x]` done with evidence - `[!]` done but flagged / unverified -
`[ ]` not done.

## Backend (FastAPI + SQLAlchemy + SQLite)

- [x] Own SQLite database file `data/subscriptions.db` (never shared) - `database.py`
- [x] Subscription ORM model with computed `monthly_cost` / `yearly_cost` - `models.py`
- [x] Pydantic v2 contracts incl. `Literal` frequency validation - `schemas.py`
- [x] CRUD layer isolated from routers - `crud.py`
- [x] `GET /health` with DB probe - `main.py`
- [x] `POST /subscriptions` (tags lowercased + de-duplicated, frequency enum, amount > 0)
- [x] `GET /subscriptions` with active/category/frequency filters (case-insensitive category)
- [x] `GET/PUT/DELETE /subscriptions/{id}` (404 handled; PUT powers "mark renewed")
- [x] `GET /renewals?days=30&include_overdue=` with `days_until_renewal` + urgency buckets
- [x] `GET /total` per-currency monthly/yearly totals + by-category + by-frequency
- [x] `GET /category/{name}` drill-down (unknown category = valid empty)
- [x] `GET /tags` distinct tag counts
- [x] 12-factor config via env vars + `.env.example` placeholders only - `config.py`

## Cost normalization service

- [x] Single source of truth for frequency math - `services/cost_calculator.py`
- [x] weekly = x 52/12, monthly = x 1, quarterly = /3, yearly = /12
- [x] Renewal advance helper (month-length clamping) used by the UI's "mark renewed"

## Integration (exposing the contract)

- [x] `GET /integration/export` versioned payload - `routers/integration.py`
- [x] Permanent `external_ref` (`B-SUB-<id>`) per subscription
- [x] Pre-normalized `monthly_cost` (consumer never re-implements frequency math)
- [x] Inactive subscriptions included with `active: false` (consumer decides)
- [x] No shared database files - B never opens A's or C's data; A only reads
      this endpoint over HTTP

## Frontend (Streamlit)

- [x] Dashboard: monthly/yearly KPIs, spend donut, 7-day renewal preview - `app.py`
- [x] Manage: table + add form + mark-renewed + activate/deactivate + delete
- [x] Renewal forecast: look-ahead slider, overdue toggle, bill-sum metric
- [x] Categories & tags exploration
- [x] Export viewer: shows the exact JSON contract A consumes
- [x] UI is a pure REST client with friendly API-down errors - `ui_common.py`

## Quality assurance

- [x] 10 pytest tests pass - `tests/` (`python -m pytest -q` -> `10 passed`)
- [x] Frequency math tested for all four frequencies (649/649, 12000/yr -> 1000/mo, 1500/qtr -> 500/mo, 100/wk -> 433.33/mo)
- [x] Validation tests: bad frequency 422, zero amount 422
- [x] Renewal window + urgency + overdue handling + sorting order
- [x] Export contract test: exact key set + `B-SUB-<id>` refs
- [x] Live smoke test (real uvicorn processes): health OK, A imported 9 active
      subs (1 inactive skipped), re-sync imported 0 -
      see `docs/FINAL_VERIFICATION_REPORT.md`
- [x] Streamlit boot check: `/_stcore/health` -> ok

## Documentation & packaging

- [x] `README.md` (features, architecture, contract, limitations)
- [x] `ENVIRONMENT_SETUP.md` (PowerShell + zsh, three-app run guide, troubleshooting)
- [x] `API_DOCUMENTATION.md` (every endpoint + examples + urgency semantics)
- [x] `RENDER_DEPLOYMENT.md` (two services, A-wiring steps, disk caveats)
- [x] `.env.example` placeholders only; `.gitignore` covers `.env`, `data/*.db`, caches
- [x] `seed_data.py` idempotent demo data (10 subscriptions across all frequencies)

## Flagged / unverified

- [!] Demo prices in `seed_data.py` are illustrative, not current vendor prices.
- [!] Render free tier: no persistent disk; SQLite resets on deploy (documented).
- [ ] Multi-currency FX conversion - out of scope, documented in README.
