"""Central configuration and invariant enforcement for CETI.

All tunable values come from environment variables with sane defaults.
Invariants are hard-coded and asserted at runtime — they cannot be overridden.
"""

import os
from typing import List, Literal

# === Environment variable loading with defaults ===
GENERATOR_MODEL: str = os.getenv("GENERATOR_MODEL", "groq/llama-3.3-70b-versatile")
CRITIC_MODEL: str = os.getenv("CRITIC_MODEL", "groq/llama-3.1-8b-instant")
JUDGE_MODELS: List[str] = os.getenv(
    "JUDGE_MODELS",
    "groq/llama-3.3-70b-versatile,groq/mixtral-8x22b-2404,groq/gemma2-27b-it"
).split(",")

MAX_ROUNDS_DEFAULT: int = int(os.getenv("MAX_ROUNDS", "5"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.92"))
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./chroma_db")

# === Hard invariants (non-overridable) ===
MIN_ADVERSARIAL_ROUNDS: int = 3                  # Invariant 1 & 4: refusal bias
MIN_QUORUM_SIZE: int = 3                         # Invariant 3: no single judge
MIN_MECHANICAL_ORTHOGONALITY_WEIGHT: float = 0.4 # Invariant 6: >=40% mechanical
DRIFT_VARIANTS_COUNT: int = 8                    # Invariant 3: rotation depth

ALLOWED_RISK_TIERS: tuple[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"], ...] = (
    "LOW", "MEDIUM", "HIGH", "CRITICAL"
)

# === Runtime invariant checks (crash on violation) ===
def enforce_invariants() -> None:
    """Called on startup — fails fast if invariants are broken."""
    if MAX_ROUNDS_DEFAULT < MIN_ADVERSARIAL_ROUNDS:
        raise AssertionError(
            f"MAX_ROUNDS must be >= {MIN_ADVERSARIAL_ROUNDS} (invariant 1 & 4)"
        )

    if len(JUDGE_MODELS) < MIN_QUORUM_SIZE:
        raise AssertionError(
            f"At least {MIN_QUORUM_SIZE} diverse judge models required (invariant 3)"
        )

    if MIN_MECHANICAL_ORTHOGONALITY_WEIGHT < 0.4:
        raise AssertionError(
            "Mechanical orthogonality weight must be >= 0.4 (invariant 6)"
        )

    print("CETI invariants enforced successfully.")

# Execute checks immediately on module import (startup validation)
enforce_invariants()
