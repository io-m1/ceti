import pytest
from unittest.mock import patch

from src.engine.verification import verify_query
from src.api.schemas import CETIResponse


@pytest.mark.asyncio
async def test_verify_query_refusal():
    """
    Test CETI refusal path:
    - Generator proposes an answer
    - Critic attacks it
    - Generator fails to satisfy orthogonality
    - Judge confirms rejection
    """
    
    # Define mock responses for each role in the adversarial loop
    async def mock_acompletion(*args, **kwargs):
        prompt_messages = kwargs.get("messages", [])
        user_content = prompt_messages[0]["content"] if prompt_messages else ""
        
        # Generator initial answer
        if "Provide an accurate, complete" in user_content:
            return {"choices": [{"message": {"content": "Test answer"}}]}
        
        # Critic attack
        if "VERDICT: ACCEPT only if the answer is PERFECT" in user_content:
            return {"choices": [{"message": {"content": "VERDICT: REJECT - Flaw detected"}}]}
        
        # Generator defense (fails)
        if "Address EVERY point raised" in user_content:
            return {"choices": [{"message": {"content": "Attempted defense, still flawed"}}]}
        
        # Judge arbitration (fallback reject)
        if "Evaluate this final answer" in user_content:
            return {"choices": [{"message": {"content": "ARBITRATED RESULT: REJECTED"}}]}
        
        # Default fallback (safe)
        return {"choices": [{"message": {"content": "VERDICT: REJECT - Flaw detected"}}]}

    # Patch the async completion used by CETI
    with patch("src.engine.verification.acompletion", side_effect=mock_acompletion):
        response: CETIResponse = await verify_query("Test query", "LOW")
    
    # Assertions
    assert response is not None
    assert response.authorization == "DENIED"
    assert response.refusal_diagnostics is not None
    assert "REJECT" in response.refusal_diagnostics.details.upper()


@pytest.mark.asyncio
async def test_verify_query_import():
    """
    Basic smoke test to ensure verify_query returns a response object.
    """
    async def mock_acompletion(*args, **kwargs):
        return {"choices": [{"message": {"content": "Test answer"}}]}
    
    with patch("src.engine.verification.acompletion", side_effect=mock_acompletion):
        response: CETIResponse = await verify_query("Test query", "LOW")
    
    assert response is not None
    assert response.authorization in ["GRANTED", "DENIED"]