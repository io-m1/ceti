from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from bcrypt import checkpw
from starlette.middleware.cors import CORSMiddleware

load_dotenv()

from src.config.settings import enforce_invariants, ALLOWED_RISK_TIERS
from src.api.schemas import CETIResponse
from src.engine.verification import verify_query

app = FastAPI(
    title="CETI",
    description="Grants scoped permission to act — never asserts truth.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    if not checkpw(x_api_key.encode(), os.getenv("API_KEY_HASH").encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

class VerifyRequest(BaseModel):
    query: str

@app.post("/verify", response_model=CETIResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def verify(request: VerifyRequest, risk_tier: str = "MEDIUM", api_key: str = Depends(verify_api_key)):
    if len(request.query) > 1000:
        raise HTTPException(status_code=400, detail="Query too long")
    if risk_tier not in ALLOWED_RISK_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid risk_tier: {', '.join(ALLOWED_RISK_TIERS)}")

    try:
        result = await verify_query(request.query, risk_tier)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")

enforce_invariants()
