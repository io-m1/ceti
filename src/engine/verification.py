from typing import Dict, Any
from litellm import acompletion
from src.config.settings import GENERATOR_MODEL
from src.engine.critics import red_team_critique
from src.ledger.vault import record_verdict

async def verify_query(query: str) -> Dict[str, Any]:
    gen_messages = [
        {"role": "system", "content": "Answer the user query truthfully and precisely."},
        {"role": "user", "content": query}
    ]

    gen_result = await acompletion(
        model=GENERATOR_MODEL,
        messages=gen_messages,
        temperature=0.2,
        max_tokens=600
    )

    response = gen_result.choices[0].message.content.strip()

    critique = await red_team_critique(query, response)

    verdict = (
        critique["verdict"] == "PASS"
        and critique["confidence"] >= 0.99
    )

    record_verdict(
        query=query,
        response=response,
        verdict=verdict,
        confidence=critique["confidence"],
        attack_summary=critique["attack_summary"]
    )

    if not verdict:
        return {
            "response": "REFUSED: Response failed adversarial verification",
            "meta": {
                "approved": False,
                "confidence": critique["confidence"],
                "attack_summary": critique["attack_summary"]
            }
        }

    return {
        "response": response,
        "meta": {
            "approved": True,
            "confidence": critique["confidence"]
        }
    }
