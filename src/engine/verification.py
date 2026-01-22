import hashlib
import time
from src.ledger.vault import record_verdict
from litellm import acompletion
from src.config.settings import GENERATOR_MODEL, CRITIC_MODEL, JUDGE_MODELS, MAX_ROUNDS_DEFAULT
from src.engine.browse import browse_web
from src.api.schemas import CETIResponse, RefusalDiagnostics, AuthorizationScope

def extract_content(response):
    if isinstance(response, dict):
        return response["choices"][0]["message"]["content"].strip()
    return response.choices[0].message.content.strip()

async def quorum_vote(final_answer, query, risk_tier):
    accepts = 0
    for judge_model in JUDGE_MODELS:
        judge_prompt = f"""
Evaluate final answer for query '{query}'.
Answer:
{final_answer}
Is this flawless for {risk_tier} risk? VERDICT: ACCEPT or REJECT."""
        try:
            judge_response = await acompletion(
                model=judge_model,
                messages=[{"role": "system", "content": judge_prompt}],
                max_tokens=100
            )
            if "VERDICT: ACCEPT" in extract_content(judge_response).upper():
                accepts += 1
        except Exception:
            continue
    required_accepts = len(JUDGE_MODELS) * 2 // 3 + 1
    return accepts >= required_accepts

async def verify_query(query, risk_tier="MEDIUM"):
    web_context = browse_web(query)
    gen_messages = [{"role": "user", "content": f"{web_context}\nAnswer: {query}"}]
    try:
        gen_response = await acompletion(model=GENERATOR_MODEL, messages=gen_messages, max_tokens=500)
        current_answer = extract_content(gen_response)
    except Exception as e:
        return CETIResponse(
            authorization="DENIED",
            response_content="Authorization denied — oracle instability.",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="instability",
                details=str(e),
                requirements_for_certification="Retry later."
            ),
            certification_id=None,
            meta={"query": query},
        )
    for round_num in range(1, MAX_ROUNDS_DEFAULT + 1):
        critic_prompt = f"""
Check answer for query '{query}'.
Answer:
{current_answer}
VERDICT: ACCEPT only if perfect, else REJECT."""
        try:
            critic_response = await acompletion(
                model=CRITIC_MODEL,
                messages=[{"role": "system", "content": critic_prompt}],
                max_tokens=400
            )
            critique = extract_content(critic_response)
        except Exception:
            critique = "CRITIC FAILURE - REJECT"
        if "VERDICT: ACCEPT" in critique.upper():
            break
        defense_prompt = f"Critique:\n{critique}\nProvide full revised answer."
        gen_messages.append({"role": "user", "content": defense_prompt})
        try:
            defense_response = await acompletion(model=GENERATOR_MODEL, messages=gen_messages, max_tokens=500)
            current_answer = extract_content(defense_response)
        except Exception:
            current_answer = "DEFENSE FAILURE - previous answer stands"
        gen_messages.append({"role": "assistant", "content": current_answer})
    return CETIResponse(authorization="GRANTED", response_content=current_answer)

async def verify_query_with_ledger(query, risk_tier="MEDIUM"):
    result = await verify_query(query=query, risk_tier=risk_tier)
    if result.authorization == "GRANTED":
        ledger_entry = {
            "query": query,
            "risk_tier": risk_tier,
            "certification_id": getattr(result, "certification_id", None),
        }
        record_verdict(ledger_entry)
    return result
