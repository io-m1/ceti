from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from src.engine.verification import verify_query_with_ledger
import os

app = FastAPI(title="CETI Consensus Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_MASTER_KEY = os.getenv("CETI_MASTER_KEY", "default-master-key")

@app.post("/verify")
async def verify(request: Request):
    body = await request.json()
    user_key = request.headers.get("Authorization", "")
    if user_key.startswith("Bearer "):
        user_key = user_key[7:]
    if user_key != API_MASTER_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    query = body.get("query")
    risk_tier = body.get("risk_tier", "MEDIUM")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")
    result = await verify_query_with_ledger(query=query, risk_tier=risk_tier)
    return result
