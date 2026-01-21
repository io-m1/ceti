from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import structlog
from python_dotenv import load_dotenv

load_dotenv()

from src.config.settings import enforce_invariants, ALLOWED_RISK_TIERS
from src.api.schemas import CETIResponse
from src.engine.verification import verify_query

logger = structlog.get_logger()

app = FastAPI(
    title="CETI",
    description="Grants scoped permission to act — never asserts truth.",
    version="1.0.0",
)

@app.on_event("startup")
async def startup():
    await FastAPILimiter.init(app)  # Rate limit setup

@app.get("/", response_model=dict)
async def health():
    logger.info("Health check accessed")
    return {
        "status": "CETI online",
        "invariants_enforced": True,
        "version": "1.0.0",
        "message": "Permission layer active — no truth assertions"
    }

async def check_api_key(authorization: str = Header(None)):
    if authorization != f"Bearer {os.getenv('API_KEY')}":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return authorization

@app.post("/verify", response_model=CETIResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def verify(query: str, risk_tier: str = "MEDIUM", api_key: str = Depends(check_api_key)):
    if risk_tier not in ALLOWED_RISK_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid risk_tier: {', '.join(ALLOWED_RISK_TIERS)}")

    try:
        result = await verify_query(query, risk_tier)
        logger.info("Verification completed", query=query, authorization=result.authorization)
        return result
    except Exception as e:
        logger.error("Verification failed", exc_info=e)
        raise HTTPException(status_code=500, detail="Internal error")

enforce_invariants()
