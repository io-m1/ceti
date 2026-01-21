import pytest
import os
from unittest.mock import AsyncMock, patch

from src.engine.verification import verify_query
from src.api.schemas import CETIResponse

@pytest.fixture(autouse=True)
def mock_groq_key():
    os.environ["GROQ_API_KEY"] = "test_key"
    yield
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]

@pytest.mark.asyncio
async def test_verify_query_refusal():
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.side_effect = [
            AsyncMock(choices=[{"message": {"content": "Test answer"}}]),
            AsyncMock(choices=[{"message": {"content": "VERDICT: REJECT - Flaw detected"}}]),
        ]
        response = await verify_query("Test query", "LOW")
        assert response.authorization == "DENIED"
        assert response.refusal_diagnostics is not None

def test_verify_query_import():
    assert verify_query is not None
