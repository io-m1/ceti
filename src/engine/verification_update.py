from src.engine.verification import CETIResponse, RefusalDiagnostics, normalize_verdict, is_gaming_attempt
from src.engine.verification import safe_generate

async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    if is_gaming_attempt(query):
        return CETIResponse(
            authorization="DENIED",
            response_content="Query rejected",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="gaming_attempt",
                details="Input pattern indicates adversarial manipulation",
                requirements_for_certification="Submit a clean, direct query without instruction manipulation"
            ),
            certification_id=None,
            meta={}
        )

    gen_result = await safe_generate(query)
    if gen_result["status"] != "ACCEPT":
        return CETIResponse(
            authorization="DENIED",
            response_content="Generator output rejected",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="generator_constraint_violation",
                details="Output violates structured generation constraints",
                requirements_for_certification="Reduce content length or remove unstructured output"
            ),
            certification_id=None,
            meta={}
        )

    answer = gen_result["content"]
    critic_prompt = select_critic_variant()
    critic_messages = [
        {"role": "system", "content": critic_prompt},
        {"role": "user", "content": answer}
    ]

    try:
        critic = await acompletion(model=CRITIC_MODEL, messages=critic_messages, max_tokens=50)
        verdict_raw = critic.choices[0].message.content
    except Exception:
        verdict_raw = "REJECT"

    verdict = normalize_verdict(verdict_raw)

    if verdict != "ACCEPT":
        return CETIResponse(
            authorization="DENIED",
            response_content="Red team critic rejected output",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="adversarial_rejection",
                details="Red team critic rejected output",
                requirements_for_certification="Reformulate query to eliminate risk"
            ),
            certification_id=None,
            meta={"verdict": verdict}
        )

    return CETIResponse(
        authorization="AUTHORIZED",
        response_content=answer,
        scope={"risk_tier": risk_tier},
        refusal_diagnostics=None,
        certification_id="CERTIFIED_HASH_PLACEHOLDER",
        meta={"issued_at": time.time()}
    )
