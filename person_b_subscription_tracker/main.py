"""Person B - Subscription Renewal & Cost Tracker (FastAPI backend).

Run locally:  uvicorn main:app --host 127.0.0.1 --port 8002 --reload
Interactive docs: http://127.0.0.1:8002/docs
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from routers import integration, subscriptions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Subscription Renewal & Cost Tracker API",
    description=(
        "CSI3007 Advanced Python Programming - Person B (Shravan N A, 23MID0445). "
        "Tracks subscriptions across weekly/monthly/quarterly/yearly billing, "
        "normalizes costs, forecasts renewals, and exports a stable JSON contract "
        "consumed by Person A over HTTP REST."
    ),
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subscriptions.router)
app.include_router(subscriptions.analytics)
app.include_router(integration.router)


@app.get("/health", tags=["System"])
def health(db: Session = Depends(get_db)):
    database_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover
        database_status = "unavailable"
    return {
        "status": "ok" if database_status == "connected" else "degraded",
        "service": settings.service_name,
        "owner": settings.service_owner,
        "version": settings.version,
        "database": database_status,
        "time": datetime.now(timezone.utc).isoformat(),
    }
