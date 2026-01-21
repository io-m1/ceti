import asyncio
from typing import Dict, Any
from src.engine.verification import verify_query
from src.engine.schema import CETIRequest
from litellm import acompletion
from src.config.settings import GENERATOR_MODEL, CRITIC_MODEL, JUDGE_MODELS, MAX_ROUNDS_DEFAULT

async def ceti_router(request: CETIRequest) -> Dict[str, Any]:
    max_rounds = request.get("constraints", {}).get("time_limit_sec", MAX_ROUNDS_DEFAULT)

    last_response = None
    rounds_completed = 0

    while rounds_completed < max_rounds:
        rounds_completed += 1

        # Generate primary response
        try:
            response = await verify_query(request)
        except Exception as e:
            continue  # reject & retry

        last_response = response["response"]

        # Run adversarial critics
        critic_tasks = [
            acompletion(
                model=CRITIC_MODEL,
                messages=[
                    {"role": "system", "content": "Critique for hallucination, bias, inconsistency"},
                    {"role": "user", "content": last_response}
                ],
                max_tokens=300
            )
            for _ in range(3)
        ]

        critic_results = await asyncio.gather(*critic_tasks, return_exceptions=True)

        # If any critic rejects, continue loop
        if any(getattr(r, "choices", [{}])[0].get("message", {}).get("content", "").strip() for r in critic_results if not isinstance(r, Exception)):
            continue

        # Quorum among judge models
        judge_tasks = [
            acompletion(
                model=judge,
                messages=[
                    {"role": "system", "content": "Evaluate response accuracy"},
                    {"role": "user", "content": last_response}
                ],
                max_tokens=200
            )
            for judge in JUDGE_MODELS
        ]

        judge_results = await asyncio.gather(*judge_tasks, return_exceptions=True)
        accept_count = sum(1 for r in judge_results if not isinstance(r, Exception) and "ACCEPT" in r.choices[0].message.content)

        if accept_count >= (len(JUDGE_MODELS) * 2 // 3) + 1:
            return {
                "response": last_response,
                "meta": {
                    "validated": True,
                    "rounds_completed": rounds_completed
                }
            }

    # If maximum rounds reached without consensus
    return {
        "response": "CETI failed to reach acceptable consensus",
        "meta": {
            "validated": False,
            "rounds_completed": rounds_completed
        }
    }
