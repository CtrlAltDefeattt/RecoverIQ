from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.api.simulations import router as simulation_router
from backend.app.api.webhooks import router as webhook_router
from backend.app.core.config import get_settings
from backend.app.storage.factory import create_recovery_repository

app = FastAPI(
    title="RecoverIQ",
    version="0.1.0",
    description="Safety-constrained adaptive revenue recovery engine",
)

app.include_router(simulation_router)
app.include_router(webhook_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "recoveriq"}


@app.get("/readiness")
def readiness():
    settings = get_settings()
    return {
        "status": "ready" if settings.webhook_configured else "degraded",
        "mode": settings.recoveriq_mode,
        "webhook_configured": settings.webhook_configured,
        "razorpay_api_configured": settings.razorpay_api_configured,
        "database_backend": settings.database_backend,
        "durable_database_configured": settings.durable_database_configured,
        "razorpay_execution_enabled": (
            settings.recoveriq_execute_razorpay_actions
            and settings.razorpay_api_configured
        ),
    }


@app.get("/health/database")
def database_health():
    """Probe the configured recovery ledger without exposing connection details."""
    settings = get_settings()
    if not settings.durable_database_configured:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "backend": settings.database_backend,
                "reachable": False,
                "reason": "durable_database_not_configured",
            },
        )

    repository = create_recovery_repository(
        database_url=settings.database_url,
        database_path=settings.recoveriq_database_path,
    )
    try:
        reachable = repository.ping()
    except Exception:
        reachable = False
    finally:
        repository.close()

    if not reachable:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "backend": settings.database_backend,
                "reachable": False,
            },
        )
    return {
        "status": "ok",
        "backend": settings.database_backend,
        "reachable": True,
    }
