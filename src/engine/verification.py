# ... (add ledger imports)

async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    cached = ledger_check(query, risk_tier)
    if cached:
        return cached

    # ... (loop)

    if consensus_reached and await quorum_vote(...):
        ledger_write(response, query, get_embedding(query))
        return response

    return response
