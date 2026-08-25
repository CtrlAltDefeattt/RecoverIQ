from fastapi import APIRouter, Query
from backend.app.simulator.benchmark import benchmark

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("/run")
def run_simulation(
    events: int = Query(default=1000, ge=100, le=100000),
    seed: int = Query(default=42),
):
    return benchmark(events=events, seed=seed)
