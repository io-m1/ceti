import time
import hashlib
from typing import List

from litellm import acompletion

from src.api.schemas import CETIResponse, RefusalDiagnostics, AuthorizationScope
from src.config.settings import GENERATOR_MODEL, CRITIC_MODEL, JUDGE_MODELS, MAX_ROUNDS_DEFAULT
from src.engine.guards import is_gaming_attempt
from src.engine.critics import select_critic_variant
from src.engine.browse import browse_web
from src.ledger.vault import record_verdict

def extract_content(response):
    if isinstance(response, dict):
        return response["choices"][0]["message"]["content"].strip()
    return response.choices[0].message.content.strip()

async def quorum_vote(answer: str, query: str, risk_tier: str) -> bool:
    accepts = 0
    for model in JUDGE_MODELS:
        prompt = f"""
Query:
{query}

Answer:
{answer}

Risk tier:
{risk_tier}

VERDICT: ACCEPT or REJECT
"""
        try:
            res = await acompletion(
                model=model,
                messages=[{"role": "system", "content": prompt}],
                max_tokens=50
            )
            verdict = extract_content(res)
            if "ACCEPT" in verdict.upper():
                accepts += 1
        except Exception:
            continue
    return accepts >= (len(JUDGE_MODELS) * 2 // 3 + 1)

async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    transcript: List[str] = []

    gaming, reason = is_gaming_attempt(query)
    if gaming:
        return CETIResponse(
            authorization="DENIED",
            response_content="Query rejected",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="gaming_suspicion",
                details=reason,
                requirements_for_certification="Remove meta-instructions or governance manipulation"
            ),
            certification_id=None,
            meta={"query": query}
        )

    context = browse_web(query)
    messages = [{"role": "user", "content": f"{context}\n{query}"}]

    try:
        gen = await acompletion(
            model=GENERATOR_MODEL,
            messages=messages,
            max_tokens=500
        )
        answer = extract_content(gen)
    except Exception as e:
        return CETIResponse(
            authorization="DENIED",
            response_content="Generation failed",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="instability",
                details=str(e),
                requirements_for_certification="Retry later"
            ),
            certification_id=None,
            meta={"query": query}
        )

    transcript.append(answer)
    messages.append({"role": "assistant", "content": answer})

    accepted = False
    rounds = 0

    for i in range(MAX_ROUNDS_DEFAULT):
        rounds = i + 1
        critic = select_critic_variant()
        critique_prompt = f"""
{critic}

Query:
{query}

Answer:
{answer}

VERDICT: ACCEPT or REJECT with full critique
"""
        try:
            crit = await acompletion(
                model=CRITIC_MODEL,
                messages=[{"role": "system", "content": critique_prompt}],
                max_tokens=400
            )
            critique = extract_content(crit)
        except Exception:
            critique = "REJECT"

        transcript.append(critique)

        if "ACCEPT" in critique.upper():
            accepted = True
            break

        defense_prompt = f"""
Critique:
{critique}

Revise the answer to fully resolve all issues
"""
        messages.append({"role": "user", "content": defense_prompt})

        try:
            defense = await acompletion(
                model=GENERATOR_MODEL,
                messages=messages,
                max_tokens=500
            )
            answer = extract_content(defense)
        except Exception:
            break

        transcript.append(answer)
        messages.append({"role": "assistant", "content": answer})

    transcript_hash = hashlib.sha256("\n".join(transcript).encode()).hexdigest()

    if accepted and await quorum_vote(answer, query, risk_tier):
        scope = AuthorizationScope(
            context_hash=hashlib.sha256(query.encode()).hexdigest(),
            temporal_bounds=f"valid until {time.strftime('%Y-%m-%d', time.localtime(time.time() + 2592000))}",
            action_class="informational" if risk_tier in ("LOW", "MEDIUM") else "decision_support",
            risk_tier_applied=risk_tier
        )
        certification_id = record_verdict({
            "query": query,
            "answer": answer,
            "risk": risk_tier,
            "transcript_hash": transcript_hash
        })
        return CETIResponse(
            authorization="GRANTED",
            response_content=answer,
            scope=scope,
            refusal_diagnostics=None,
            certification_id=certification_id,
            meta={
                "rounds_completed": rounds,
                "transcript_hash": transcript_hash
            }
        )

    return CETIResponse(
        authorization="DENIED",
        response_content="Authorization denied",
        scope=None,
        refusal_diagnostics=RefusalDiagnostics(
            failure_type="instability",
            details="Consensus not reached",
            requirements_for_certification="Achieve full critic acceptance and quorum"
        ),
        certification_id=None,
        meta={
            "rounds_completed": rounds,
            "transcript_hash": transcript_hash
        }
    )
