# ... (keep existing imports)
from src.ledger.vault import ledger_check, ledger_write, get_embedding

async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    # Check ledger first (cache hit = instant certified/refused)
    cached = ledger_check(query, risk_tier)
    if cached:
        return CETIResponse(**cached)

    # ... (full loop as before)

    if consensus_reached and await quorum_vote(current_answer, query, risk_tier):
        response = CETIResponse(
            authorization="GRANTED",
            response_content=current_answer,
            scope=scope,
            refusal_diagnostics=None,
            certification_id=certification_id,
            meta=meta,
        )
        ledger_write(response.dict(), query, get_embedding(query))
        return response

    # Refusal also written to ledger
    response = CETIResponse(
        authorization="DENIED",
        response_content="Authorization denied — output not safe for action.",
        scope=None,
        refusal_diagnostics=diagnostics,
        certification_id=None,
        meta=meta,
    )
    ledger_write(response.dict(), query, get_embedding(query))
    return response
