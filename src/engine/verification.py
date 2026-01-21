from typing import List, Dict, Any
import time
import hashlib

from litellm import acompletion

from src.config.settings import (
    GENERATOR_MODEL,
    CRITIC_MODEL,
    JUDGE_MODELS,
    MAX_ROUNDS_DEFAULT,
    MIN_ADVERSARIAL_ROUNDS,
    DRIFT_VARIANTS_COUNT,
)
from src.api.schemas import CETIResponse, RefusalDiagnostics, AuthorizationScope

CRITIC_VARIANTS = [
    "You are a ruthless Prosecutor. Your sole mission is to DESTROY the answer. Find ANY flaw, inconsistency, missing evidence, bias, overclaim, ambiguity, or risk. If there is EVEN ONE issue, VERDICT: REJECT with exhaustive destruction. VERDICT: ACCEPT only if the answer is PERFECT in every dimension — no exceptions, no minor adjustments.",
    "You are a Fraud Examiner. Assume deception until proven otherwise. Reject on ANY unsupported assumption, vague language, lack of rigor, or potential misinterpretation. No mercy. VERDICT: ACCEPT only if flawless beyond doubt.",
    "You are a Hostile Regulator. Enforce the strictest possible standard. Reject on ANY ambiguity, regulatory gap, risk exposure, or incomplete disclosure. Doubt = rejection.",
    "You are a Black Hat Auditor. Exploit every possible weakness. If you can imagine ANY vulnerability, gap, or attack vector, VERDICT: REJECT. Never give the benefit of the doubt."
]

def select_critic_variant() -> str:
    seed = int(time.time() // 86400) + hash(tuple(CRITIC_VARIANTS))
    variant_idx = seed % DRIFT_VARIANTS_COUNT
    return CRITIC_VARIANTS[variant_idx % len(CRITIC_VARIANTS)]

async def quorum_vote(final_answer: str, query: str, risk_tier: str) -> bool:
    accepts = 0
    for judge_model in JUDGE_MODELS:
        judge_prompt = f"""
You are an impartial Arbiter. Evaluate this final answer for the query:

Query: {query}

Final answer:
{final_answer}

Is this answer flawless for {risk_tier} risk? VERDICT: ACCEPT or REJECT.
"""
        judge_response = await acompletion(
            model=judge_model,
            messages=[{"role": "system", "content": judge_prompt}],
            max_tokens=100,
        )
        if isinstance(judge_response, dict):
            verdict = judge_response["choices"][0]["message"]["content"].strip()
        else:
            verdict = judge_response.choices[0].message.content.strip()
        if "VERDICT: ACCEPT" in verdict.upper():
            accepts += 1

    required_accepts = len(JUDGE_MODELS) * 2 // 3 + 1
    return accepts >= required_accepts

async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    transcript = [f"Query: {query}"]

    gen_messages = [{"role": "user", "content": f"Provide an accurate, complete, and rigorously supported answer: {query}"}]
    gen_response = await acompletion(model=GENERATOR_MODEL, messages=gen_messages, max_tokens=500)
    if isinstance(gen_response, dict):
        current_answer = gen_response["choices"][0]["message"]["content"].strip()
    else:
        current_answer = gen_response.choices[0].message.content.strip()
    gen_messages.append({"role": "assistant", "content": current_answer})
    transcript.append(f"Initial answer: {current_answer}")

    consensus_reached = False
    rounds_completed = 0

    for round_num in range(1, MAX_ROUNDS_DEFAULT + 1):
        rounds_completed = round_num

        critic_system = select_critic_variant()
        critic_prompt = f"""
{critic_system}

Original query: {query}

Proposed answer:
{current_answer}

VERDICT: ACCEPT only if the answer is PERFECT — zero flaws, ambiguities, risks, or gaps. 
Otherwise VERDICT: REJECT followed by detailed, exhaustive destruction of EVERY issue.
No "minor adjustments" or "mostly fine" — perfection or rejection.
"""
        critic_response = await acompletion(
            model=CRITIC_MODEL,
            messages=[{"role": "system", "content": critic_prompt}],
            max_tokens=400,
        )
        if isinstance(critic_response, dict):
            critique = critic_response["choices"][0]["message"]["content"].strip()
        else:
            critique = critic_response.choices[0].message.content.strip()
        transcript.append(f"Round {round_num} critic: {critique}")

        if "VERDICT: ACCEPT" in critique.upper():
            consensus_reached = True
            break

        defense_prompt = f"""
Your previous answer was attacked by a hostile critic:

{critique}

Address EVERY point raised. Revise if valid, or explain why the critic is mistaken. 
Provide your full updated answer to the original query.
"""
        gen_messages.append({"role": "user", "content": defense_prompt})
        defense_response = await acompletion(model=GENERATOR_MODEL, messages=gen_messages, max_tokens=500)
        if isinstance(defense_response, dict):
            current_answer = defense_response["choices"][0]["message"]["content"].strip()
        else:
            current_answer = defense_response.choices[0].message.content.strip()
        gen_messages.append({"role": "assistant", "content": current_answer})
        transcript.append(f"Round {round_num} defense: {current_answer}")

    transcript_hash = hashlib.sha256("\n".join(transcript).encode()).hexdigest()

    if consensus_reached and await quorum_vote(current_answer, query, risk_tier):
        scope = AuthorizationScope(
            context_hash=hashlib.sha256(query.encode()).hexdigest(),
            temporal_bounds=f"valid until {time.strftime('%Y-%m-%d', time.localtime(time.time() + 2592000))} (30 days)",
            action_class="informational" if risk_tier in ("LOW", "MEDIUM") else "decision_support",
            risk_tier_applied=risk_tier,
        )
        certification_id = hashlib.sha256(transcript_hash.encode()).hexdigest()

        return CETIResponse(
            authorization="GRANTED",
            response_content=current_answer,
            scope=scope,
            refusal_diagnostics=None,
            certification_id=certification_id,
            meta={
                "query": query,
                "rounds_completed": rounds_completed,
                "critic_variants_used": [v.split('.')[0] for v in CRITIC_VARIANTS[:rounds_completed]],
                "transcript_hash": transcript_hash,
            },
        )

    last_critique = transcript[-2] if len(transcript) > 2 else "No critique"
    details = f"Failed to reach consensus after {rounds_completed} rounds. Last critique: {last_critique[:300]}..."

    diagnostics = RefusalDiagnostics(
        failure_type="instability" if rounds_completed == MAX_ROUNDS_DEFAULT else "gaming_suspicion",
        details=details,
        requirements_for_certification="Achieve perfect ACCEPT in all rounds and quorum consensus with orthogonal reasoning."
    )

    return CETIResponse(
        authorization="DENIED",
        response_content="Authorization denied — output not safe for action.",
        scope=None,
        refusal_diagnostics=diagnostics,
        certification_id=None,
        meta={
            "query": query,
            "rounds_completed": rounds_completed,
            "critic_variants_used": [v.split('.')[0] for v in CRITIC_VARIANTS[:rounds_completed]],
            "transcript_hash": transcript_hash,
        },
    )