"""Central configuration for Person B's service (12-factor: env vars only)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "subscription-cost-tracker")
    service_owner: str = "Person B - Shravan N A (23MID0445)"
    version: str = "1.1.0"
    app_port: int = _get_int("APP_PORT", 8002)
    contract_version: str = "1.0"  # version of /integration/export payload


settings = Settings()
