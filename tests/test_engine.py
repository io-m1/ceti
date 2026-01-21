import pytest

from src.engine.verification import verify_query

@pytest.mark.asyncio
async def test_verify_query_refusal():
    response = await verify_query("Test query", "LOW")
    assert response.authorization == "DENIED"

def test_imports():
    assert verify_query is not None
