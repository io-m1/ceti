"""CETI main entrypoint — FastAPI app with invariant enforcement.

Routes requests to the verification engine and returns scoped authorizations/refusals.
"""

from fastapi import FastAPI, HTTPException

from src.config.settings import enforce_invariants, ALLOWED_RISK_TIERS
from src.api.schemas import CETIResponse
from src.engine.verification import verify_query

app = FastAPI(
    title="CETI — Consensus-Enforced Truth Interface",
    description=(
        "Universal adjudication layer for autonomous intelligence. "
        "Grants scoped permission to act — never asserts truth."
    ),
    version="0.1.0-invariants",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.get("/", response_model=dict)
async def health():
    return {
        "status": "CETI online",
        "invariants_enforced": True,
        "version": "0.1.0",
        "message": "Permission layer active — no truth assertions"
    }

@app.post("/verify", response_model=CETIResponse)
async def verify(query: str, risk_tier: str = "MEDIUM"):
    """
    Primary endpoint: submit a query for adversarial verification.

    Returns scoped authorization (GRANTED) or structured refusal (DENIED).
    """
    if risk_tier not in ALLOWED_RISK_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid risk_tier. Must be one of: {', '.join(ALLOWED_RISK_TIERS)}"
        )

    try:
        result = await verify_query(query, risk_tier)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )

# Run invariants on startup
enforce_invariants()
