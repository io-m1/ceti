from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import os
from dotenv import load_dotenv
import logging

load_dotenv()

from src.config.settings import enforce_invariants, ALLOWED_RISK_TIERS
from src.api.schemas import CETIResponse
from src.engine.verification import verify_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CETI — Consensus-Enforced Truth Interface",
    description="Grants scoped permission to act — never asserts truth.",
    version="1.0.0",
)

@app.on_event("startup")
async def startup():
    redis_client = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_client)

@app.get("/", response_model=dict)
async def health():
    return {
        "status": "CETI online",
        "invariants_enforced": True,
        "version": "1.0.0",
        "message": "Permission layer active — no truth assertions"
    }

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@app.post("/verify", response_model=CETIResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def verify(query: str, risk_tier: str = "MEDIUM", api_key: str = Depends(verify_api_key)):
    if risk_tier not in ALLOWED_RISK_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid risk_tier: {', '.join(ALLOWED_RISK_TIERS)}")

    try:
        result = await verify_query(query, risk_tier)
        logger.info("Query processed", query=query, risk_tier=risk_tier, authorization=result.authorization)
        return result
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", query=query, risk_tier=risk_tier)
        raise HTTPException(status_code=500, detail=str(e))

enforce_invariants()
