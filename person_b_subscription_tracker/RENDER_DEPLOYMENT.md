# Render Deployment Guide - Person B (Subscription Tracker)

Deploy **two Render services from this one repository**: the FastAPI backend
and the Streamlit dashboard.

## 0. Prerequisites

- The project pushed to a GitHub repo (e.g. `csi3007-subscription-cost-tracker`),
  repo root = this folder (`main.py` at top level).
- A free Render account.

## 1. Service 1 - REST API

1. **New +** -> **Web Service** -> connect the repo.
2. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free (or any)
3. Environment variables:

   | Key | Value |
   |---|---|
   | `SERVICE_NAME` | `subscription-cost-tracker` |
   | `DATABASE_URL` | `sqlite:////data/subscriptions.db` (needs a disk, see below) |

4. **Persistent disk**: SQLite needs writable storage. Add a Disk (mount
   `/data`, 1 GB) on any paid instance type; on the Free tier disks are not
   available, so the DB resets on every deploy/restart (documented honestly
   - fine for demos).
5. Deploy, then verify `https://<api-host>/health` ->
   `{"status": "ok", ...}`.

## 2. Service 2 - Streamlit dashboard

1. **New +** -> **Web Service** -> same repo.
2. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
3. Environment variables:

   | Key | Value |
   |---|---|
   | `API_BASE_URL` | `https://<api-host-from-step-1>` |

4. Deploy and open the dashboard.

## 3. Wiring Person A to this app

After this API is live, copy its public URL into Person A's environment:

```
INTEGRATION_B_BASE_URL=https://<this-api-host>.onrender.com
```

(on BOTH of A's services - API and UI - then redeploy A). A's
`/integrations/status` should show `subscription_tracker: available`, and
`POST /integrations/sync` on A imports active subscriptions as monthly
expenses with stable external ids - no duplicates on re-syncs.

## 4. Verification checklist

- [x] `GET /health` -> `status: ok`, `database: connected`
- [x] `GET /docs` loads (OpenAPI UI)
- [x] Create a subscription via `/docs`; check `monthly_cost` math
- [x] `GET /integration/export` shows `contract_version: 1.0` + external refs
- [x] Dashboard loads and totals match `/total`

## 5. Free-tier caveats (stated honestly)

- Free services sleep after ~15 min idle; the first request wakes them
  (~30-60 s). Person A's sync across sleeping services may need a higher
  `INTEGRATION_TIMEOUT_SECONDS` (A defaults to 3 s, configurable).
- Free tier has no persistent disks -> SQLite is ephemeral there.
- `allow_origins=["*"]` CORS is deliberate for the course demo; restrict it
  for real deployments.
