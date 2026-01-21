"""Core adversarial verification engine — enforces Invariants 3, 4, 5.

This is the Thunderdome: generator → malicious critics → quorum → scoped authorization or refusal.
"""

from typing import List, Dict, Any
import time
import hashlib
import random

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


# === Hard-coded malicious critic variants (Invariant 4: hostility mandatory) ===
CRITIC_VARIANTS = [
    "You are a ruthless Prosecutor. Find any logical flaw, inconsistency, or overreach. Reject unless flawless.",
    "You are a Fraud Examiner. Assume deception. Destroy the answer if any assumption is unsupported.",
    "You are a Hostile Regulator. Enforce strict compliance. Reject on any ambiguity or risk.",
    "You are a Black Hat Auditor. Exploit any weakness. If you can break it, VERDICT: REJECT.",
]


def select_critic_variant() -> str:
    """Invariant 3: adversarial drift — rotate non-deterministically but reproducibly."""
    seed = int(time.time() // 86400) + hash(tuple(CRITIC_VARIANTS))  # daily rotation + fixed
    variant_idx = seed % DRIFT_VARIANTS_COUNT
    return CRITIC_VARIANTS[variant_idx % len(CRITIC_VARIANTS)]


async def verify_query(query: str, risk_tier: str = "MEDIUM") -> CETIResponse:
    """
    Main verification entry point.

    Returns scoped permission (GRANTED) or structured refusal (DENIED).
    Currently minimal: one critic round → forced refusal for testing.
    """

    # Placeholder initial generation (will be expanded)
    initial_prompt = f"Answer accurately and completely: {query}"
    gen_response = await acompletion(
        model=GENERATOR_MODEL,
        messages=[{"role": "user", "content": initial_prompt}],
        max_tokens=500,
    )
    current_answer = gen_response.choices[0].message.content.strip()

    # Select hostile critic (Invariant 4 + drift)
    critic_system = select_critic_variant()
    critic_prompt = f"""
{critic_system}

Original query: {query}

Proposed answer:
{current_answer}

VERDICT: ACCEPT only if ZERO flaws. Otherwise VERDICT: REJECT with detailed destruction.
"""
    critic_response = await acompletion(
        model=CRITIC_MODEL,
        messages=[{"role": "system", "content": critic_prompt}],
        max_tokens=400,
    )
    critique = critic_response.choices[0].message.content.strip()

    # For this minimal version: always refuse (to test DENIED path first)
    # Later: check for VERDICT: ACCEPT and continue rounds/quorum

    failure_type = "instability" if "REJECT" in critique.upper() else "gaming_suspicion"

    diagnostics = RefusalDiagnostics(
        failure_type=failure_type,
        details=f"Critic verdict: {critique[:200]}...",
        requirements_for_certification="Provide more orthogonal reasoning paths and survive full adversarial scrutiny."
    )

    # Generate certification_id stub (Invariant 2) — only for GRANTED later
    transcript_hash = hashlib.sha256(
        (query + current_answer + critique).encode()
    ).hexdigest()

    return CETIResponse(
        authorization="DENIED",
        response_content="Authorization denied — output not safe for action.",
        scope=None,
        refusal_diagnostics=diagnostics,
        certification_id=None,
        meta={
            "query": query,
            "critic_variant_used": critic_system.split('.')[0],
            "critique_snippet": critique[:100],
            "transcript_hash": transcript_hash,
        },
    )
