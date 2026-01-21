from typing import TypedDict, Literal, Dict
from datetime import datetime

IntentType = Literal["question", "instruction", "assertion", "data_request"]
RiskClass = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

class Constraints(TypedDict):
    truth_required: bool
    hallucination_intolerance: float
    time_limit_sec: int

class Metadata(TypedDict):
    session_id: str
    user_hash: str
    timestamp: str

class CETIRequest(TypedDict):
    intent_type: IntentType
    content: str
    risk_class: RiskClass
    constraints: Constraints
    metadata: Metadata
