# Environment Setup - Person B (Subscription Tracker)

Target: Python **3.11 or 3.12** (tested on 3.12). No database server needed -
the app uses its own SQLite file under `data/`.

---

## Windows (PowerShell)

```powershell
# 1. Verify Python
python --version          # expect 3.11+

# 2. Create and activate a virtual environment (inside the project folder)
cd person_b_subscription_tracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If script execution is blocked:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Configuration
Copy-Item .env.example .env

# 5. Seed demo data (optional)
python seed_data.py

# 6. Run the backend (keep this terminal open)
uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# 7. Run the frontend in a SECOND terminal (activate venv first)
.\.venv\Scripts\Activate.ps1
$env:API_BASE_URL = "http://127.0.0.1:8002"
streamlit run app.py
```

Dashboard: <http://localhost:8502> - API docs: <http://127.0.0.1:8002/docs>

## macOS (zsh)

```zsh
# 1. Verify Python
python3 --version         # expect 3.11+

# 2. Create and activate a virtual environment (inside the project folder)
cd person_b_subscription_tracker
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
python3 -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env

# 5. Seed demo data (optional)
python seed_data.py

# 6. Run the backend (keep this terminal open)
uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# 7. Run the frontend in a SECOND terminal (activate venv first)
source .venv/bin/activate
export API_BASE_URL="http://127.0.0.1:8002"
streamlit run app.py
```

## Running all three teammates' apps together (integration demo)

| App | Backend port | Frontend port |
|---|---|---|
| **B - this app** | 8002 | 8502 |
| C - Smart Home Energy | 8003 | 8503 |
| A - Expense & Budget | 8001 | 8501 |

Start backends in separate terminals (see each app's setup guide), then in
Person A's `.env` point `SUBSCRIPTION_API_URL=http://127.0.0.1:8002`.
A's **Integrations** page will show this app as `available` and its sync will
import active subscriptions as monthly expenses.

## Tests

```bash
python -m pytest -q          # 10 tests, uses a throwaway SQLite file
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Activate.ps1 cannot be loaded` | PowerShell policy - see step 2 comment. |
| Streamlit shows "Cannot reach API" | Backend not running, or `API_BASE_URL` mismatch. |
| Port 8002 already in use | Change `--port` (and restart the UI with matching `API_BASE_URL`). |
| `database is locked` | Only the API process should open `data/subscriptions.db`. |
| Person A's sync imports nothing | Add subscriptions (or run `seed_data.py`) - the export is live data, not fixtures. |
