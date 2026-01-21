"""Core adversarial verification engine — enforces Invariants 3, 4, 5.

Full Thunderdome + ledger integration.
"""

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
from src.ledger.vault import ledger_check, ledger_write
from src.utils.embeddings import get_embedding


# === Hard-coded malicious critic variants ===
CRITIC_VARIANTS = [...]  # Same as before, omitted for brevity

def select_critic_variant() -> str:
    # Same as before

async def quorum_vote(final_answer: str, query: str, risk_tier: str) -> bool:
    # Same as before

async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    """
    Main verification entrypoint — ledger check + full Thunderdome.
    """

    # Ledger check first (Invariant 6)
    query_embedding = get_embedding(query)
    cached_response = ledger_check(query, risk_tier)
    if cached_response:
        return cached_response

    transcript = [f"Query: {query}"]

    # Initial generation
    gen_messages = [{"role": "user", "content": f"Provide an accurate, complete, and rigorously supported answer: {query}"}]
    gen_response = await acompletion(model=GENERATOR_MODEL, messages=gen_messages, max_tokens=500)
    current_answer = gen_response.choices[0].message.content.strip()
    gen_messages.append({"role": "assistant", "content": current_answer})
    transcript.append(f"Initial answer: {current_answer}")

    consensus_reached = False
    rounds_completed = 0

    for round_num in range(1, MAX_ROUNDS_DEFAULT + 1):
        rounds_completed = round_num

        # Critic attack
        critic_system = select_critic_variant()
        critic_prompt = # Same as before
        critic_response = await acompletion(model=CRITIC_MODEL, messages=[{"role": "system", "content": critic_prompt}], max_tokens=400)
        critique = critic_response.choices[0].message.content.strip()
        transcript.append(f"Round {round_num} critic: {critique}")

        if "VERDICT: ACCEPT" in critique.upper():
            consensus_reached = True
            break

        # Defense
        defense_prompt = # Same as before
        gen_messages.append({"role": "user", "content": defense_prompt})
        defense_response = await acompletion(model=GENERATOR_MODEL, messages=gen_messages, max_tokens=500)
        current_answer = defense_response.choices[0].message.content.strip()
        gen_messages.append({"role": "assistant", "content": current_answer})
        transcript.append(f"Round {round_num} defense: {current_answer}")

    transcript_hash = hashlib.sha256("\n".join(transcript).encode()).hexdigest()

    if consensus_reached and await quorum_vote(current_answer, query, risk_tier):
        # GRANTED
        scope = AuthorizationScope(
            context_hash=hashlib.sha256(query.encode()).hexdigest(),
            temporal_bounds=f"valid until {time.strftime('%Y-%m-%d', time.localtime(time.time() + 2592000))} (30 days)",
            action_class="informational" if risk_tier in ("LOW", "MEDIUM") else "decision_support",
            risk_tier_applied=risk_tier,
        )
        certification_id = hashlib.sha256(transcript_hash.encode()).hexdigest()

        response = CETIResponse(
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

        # Write to ledger
        ledger_write(response, query, query_embedding)

        return response

    # DENIED
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
