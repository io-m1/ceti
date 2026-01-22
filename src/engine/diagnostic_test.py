#!/usr/bin/env python3
import asyncio
import os
from src.engine.verification import verify_query
from src.config.settings import GENERATOR_MODEL, CRITIC_MODEL, JUDGE_MODELS

async def main():
    os.environ["SERPER_API_KEY"] = "a27606362c3b090dc8cc91ed813a2a8617342603"

    query = "Latest AI news 2026?"
    risk_tier = "HIGH"

    print(f"Running CETI verification for query: {query}\nRisk tier: {risk_tier}\n")
    result = await verify_query(query=query, risk_tier=risk_tier)
    print("CETI response:")
    print(result.json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
