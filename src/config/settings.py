import os
from typing import List, Literal, Tuple

# ────────────────────────────────────────────────
# CETI Central Configuration & Invariants
# ────────────────────────────────────────────────

GENERATOR_MODEL: str = os.getenv("GENERATOR_MODEL", "groq/llama-3.3-70b-versatile")
CRITIC_MODEL: str = os.getenv("CRITIC_MODEL", "groq/llama-3.1-8b-instant")
JUDGE_MODELS: List[str] = os.getenv(
    "JUDGE_MODELS",
    "groq/llama-3.3-70b-versatile,groq/mixtral-8x22b-2404,groq/gemma2-27b-it"
).split(",")

MAX_ROUNDS_DEFAULT: int = int(os.getenv("MAX_ROUNDS", "5"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.92"))
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./chroma_db")

# Hard invariants (crash if violated)
MIN_ADVERSARIAL_ROUNDS: int = 3
MIN_QUORUM_SIZE: int = 3
MIN_MECHANICAL_ORTHOGONALITY_WEIGHT: float = 0.4
DRIFT_VARIANTS_COUNT: int = 8

ALLOWED_RISK_TIERS: Tuple[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"], ...] = (
    "LOW", "MEDIUM", "HIGH", "CRITICAL"
)

# Optional model validation set
SUPPORTED_MODELS = {
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.1-8b-instant",
    "groq/mixtral-8x22b-2404",
    "groq/gemma2-27b-it"
}

def enforce_invariants() -> None:
    """Fail-fast on startup if invariants are broken."""
    if MAX_ROUNDS_DEFAULT < MIN_ADVERSARIAL_ROUNDS:
        raise AssertionError(f"MAX_ROUNDS must be >= {MIN_ADVERSARIAL_ROUNDS}")

    if len(JUDGE_MODELS) < MIN_QUORUM_SIZE:
        raise AssertionError(f"At least {MIN_QUORUM_SIZE} judge models required")

    if MIN_MECHANICAL_ORTHOGONALITY_WEIGHT < 0.4:
        raise AssertionError("Mechanical orthogonality weight must be >= 0.4")

    for m in [GENERATOR_MODEL, CRITIC_MODEL] + JUDGE_MODELS:
        if m not in SUPPORTED_MODELS:
            raise AssertionError(f"Unsupported model: {m}")

    print("CETI invariants enforced successfully.")

# Run checks immediately
enforce_invariants()