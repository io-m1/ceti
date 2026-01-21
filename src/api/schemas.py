"""Strict response schemas for CETI — enforces Invariant 5 (permission, not truth).

All outputs are scoped authorizations or refusals — never truth assertions.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class RefusalDiagnostics(BaseModel):
    """Structured diagnostics for DENIED responses (actionable for user/agent)."""

    failure_type: Literal[
        "correlation_suspicion",
        "contradiction",
        "gaming_suspicion",
        "missing_evidence",
        "instability",
        "other"
    ]
    details: str = Field(..., description="Explanation of what failed")
    requirements_for_certification: Optional[str] = Field(
        None, description="What would allow certification (if actionable)"
    )


class AuthorizationScope(BaseModel):
    """Scoped bounds for granted authorization (Invariant 1 & 5)."""

    context_hash: str = Field(..., description="Hash of query + relevant context")
    temporal_bounds: str = Field(..., description="e.g., 'valid until 2026-02-21'")
    action_class: str = Field(..., description="e.g., 'informational', 'decision_support'")
    risk_tier_applied: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class CETIResponse(BaseModel):
    """Final response schema — only permission or denial, never truth claims."""

    authorization: Literal["GRANTED", "DENIED"]
    response_content: str = Field(..., description="The generated output (if GRANTED)")
    scope: Optional[AuthorizationScope] = Field(
        None, description="Only present if GRANTED"
    )
    refusal_diagnostics: Optional[RefusalDiagnostics] = Field(
        None, description="Only present if DENIED"
    )
    certification_id: Optional[str] = Field(
        None,
        description="Unique traceable ID only if GRANTED (Invariant 2)",
        pattern=r"^[a-f0-9]{64}$",  # SHA-256 hex
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Non-authoritative metadata (e.g., agents_used, iterations)",
    )

    class Config:
        extra = "forbid"  # No unknown fields allowed
