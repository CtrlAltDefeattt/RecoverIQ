from fastapi import FastAPI
from backend.app.api.simulations import router as simulation_router
from backend.app.api.webhooks import router as webhook_router

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
