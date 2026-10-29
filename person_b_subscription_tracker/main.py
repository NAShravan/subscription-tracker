"""Person B - Subscription Renewal & Cost Tracker (FastAPI backend).

Run locally:  uvicorn main:app --host 127.0.0.1 --port 8002 --reload
Production:   uvicorn main:app --host 0.0.0.0 --port $PORT
Interactive docs: http://127.0.0.1:8002/docs
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from database import Base, database_backend, engine, get_db
from routers import integration, subscriptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("subscription_tracker")


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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the traceback server-side; return a generic JSON 500 to clients."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", include_in_schema=False)
def root():
    return {"service": settings.service_name, "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["System"])
def health(db: Session = Depends(get_db)):
    """Liveness (always 200 while running) + database readiness field."""
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
        "database_backend": database_backend(),
        "time": datetime.now(timezone.utc).isoformat(),
    }
