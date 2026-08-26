from fastapi import FastAPI
from backend.app.api.simulations import router as simulation_router
from backend.app.api.webhooks import router as webhook_router
from backend.app.core.config import get_settings

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
        "razorpay_execution_enabled": (
            settings.recoveriq_execute_razorpay_actions
            and settings.razorpay_api_configured
        ),
    }
