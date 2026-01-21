from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict, Any
import uuid

ALLOWED_INTENTS = {"question", "instruction", "assertion", "data_request"}
ALLOWED_RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

def normalize_plain_english(
    text: str,
    intent_type: str = "question",
    risk_class: str = "MEDIUM",
    truth_required: bool = True,
    hallucination_intolerance: float = 0.05,
    time_limit_sec: int = 60,
    user_identity: str = "anonymous"
) -> Dict[str, Any]:

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Invalid content")

    if intent_type not in ALLOWED_INTENTS:
        raise ValueError("Invalid intent_type")

    if risk_class not in ALLOWED_RISKS:
        raise ValueError("Invalid risk_class")

    if not 0 <= hallucination_intolerance <= 1:
        raise ValueError("Invalid hallucination_intolerance")

    if not 1 <= time_limit_sec <= 120:
        raise ValueError("Invalid time_limit_sec")

    timestamp = datetime.now(timezone.utc).isoformat()

    user_hash = sha256(user_identity.encode()).hexdigest()

    payload = {
        "intent_type": intent_type,
        "content": text.strip(),
        "risk_class": risk_class,
        "constraints": {
            "truth_required": truth_required,
            "hallucination_intolerance": hallucination_intolerance,
            "time_limit_sec": time_limit_sec
        },
        "metadata": {
            "session_id": str(uuid.uuid4()),
            "user_hash": user_hash,
            "timestamp": timestamp
        }
    }

    return payload
