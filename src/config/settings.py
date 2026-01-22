import os
from typing import List, Literal

GENERATOR_MODEL = os.getenv(
    "GENERATOR_MODEL",
    "groq/llama3-groq-70b-8192-tool-use-preview"
)
CRITIC_MODEL = os.getenv(
    "CRITIC_MODEL",
    "groq/llama3-groq-70b-8192-tool-use-preview"
)

JUDGE_MODELS = os.getenv(
    "JUDGE_MODELS",
    "groq/llama3-groq-70b-8192-tool-use-preview,groq/mixtral-8x7b-32768,groq/gemma2-27b-it"
).split(",")

MAX_ROUNDS_DEFAULT = int(os.getenv("MAX_ROUNDS", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.92"))
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

ALLOWED_RISK_TIERS: tuple[Literal["LOW","MEDIUM","HIGH","CRITICAL"], ...] = (
    "LOW", "MEDIUM", "HIGH", "CRITICAL"
)

MIN_ADVERSARIAL_ROUNDS = int(os.getenv("MIN_ADVERSARIAL_ROUNDS", "3"))
MIN_QUORUM_SIZE = int(os.getenv("MIN_QUORUM_SIZE", "3"))
MIN_MECHANICAL_ORTHOGONALITY_WEIGHT = float(os.getenv("MIN_MECHANICAL_ORTHOGONALITY_WEIGHT", "0.4"))
DRIFT_VARIANTS_COUNT = int(os.getenv("DRIFT_VARIANTS_COUNT", "8"))

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

API_MASTER_KEY = os.getenv("CETI_MASTER_KEY", "default-master-key")

def enforce_invariants():
    if MAX_ROUNDS_DEFAULT < MIN_ADVERSARIAL_ROUNDS:
        raise AssertionError("MAX_ROUNDS must be >= MIN_ADVERSARIAL_ROUNDS")
    if len(JUDGE_MODELS) < MIN_QUORUM_SIZE:
        raise AssertionError("At least MIN_QUORUM_SIZE judge models required")
    if MIN_MECHANICAL_ORTHOGONALITY_WEIGHT < 0.4:
        raise AssertionError("Mechanical orthogonality weight must be >= 0.4")
    if not SERPER_API_KEY:
        raise AssertionError("SERPER_API_KEY missing in environment")
    if not GROQ_API_KEY:
        raise AssertionError("GROQ_API_KEY missing in environment")
    if not DEEPSEEK_API_KEY:
        raise AssertionError("DEEPSEEK_API_KEY missing in environment")
    print("CETI invariants enforced successfully.")

enforce_invariants()
