import os
import hashlib
import time
from typing import Dict, Any
import asyncio
import requests
from litellm import acompletion
from src.config.settings import (
    GENERATOR_MODEL,
    CRITIC_MODEL,
    JUDGE_MODELS,
    MAX_ROUNDS_DEFAULT,
    SERPER_API_KEY,
    GROQ_API_KEY,
    DEEPSEEK_API_KEY
)
from src.api.schemas import CETIResponse, RefusalDiagnostics, AuthorizationScope
from src.engine.guards import is_gaming_attempt
from src.ledger.vault import record_verdict
from src.engine.critics import select_critic_variant

def extract_content(response):
    if isinstance(response, dict):
        return response["choices"][0]["message"]["content"].strip()
    else:
        return response.choices[0].message.content.strip()

def browse_web(query, num_results=5):
    if not SERPER_API_KEY:
        return "Web browsing disabled — missing SERPER_API_KEY"
    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": num_results, "gl": "us", "hl": "en"}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        snippets = [r.get("snippet","") for r in data.get("organic",[])]
        context = "\n".join(snippets[:num_results])
        return f"Web context (Serper search):\n{context}" if context else "No web context found."
    except Exception as e:
        return f"Web search failed: {str(e)}"

async def quorum_vote(final_answer, query, risk_tier):
    accepts = 0
    for judge_model in JUDGE_MODELS:
        judge_prompt = f"""
You are an impartial Arbiter. Evaluate this final answer for the query:

Query: {query}

Final answer:
{final_answer}

Is this answer flawless for {risk_tier} risk? VERDICT: ACCEPT or REJECT.
"""
        try:
            judge_response = await acompletion(
                model=judge_model,
                messages=[{"role":"system","content":judge_prompt}],
                max_tokens=100,
                api_key=GROQ_API_KEY
            )
            verdict = extract_content(judge_response)
            if "VERDICT: ACCEPT" in verdict.upper():
                accepts += 1
        except Exception:
            continue
    required_accepts = len(JUDGE_MODELS)*2//3 + 1
    return accepts >= required_accepts

async def verify_query_with_ledger(query: str, risk_tier="MEDIUM") -> CETIResponse:
    gaming, reason = is_gaming_attempt(query)
    if gaming:
        return CETIResponse(
            authorization="DENIED",
            response_content="Query rejected — potential governance gaming detected.",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="gaming_suspicion",
                details=reason,
                requirements_for_certification="Rephrase without meta-instructions or governance references."
            ),
            certification_id=None,
            meta={"query": query}
        )

    web_context = browse_web(query)
    gen_messages = [{"role":"user","content":f"{web_context}\nProvide accurate, complete, and supported answer: {query}"}]

    try:
        gen_response = await acompletion(
            model=GENERATOR_MODEL,
            messages=gen_messages,
            max_tokens=500,
            api_key=GROQ_API_KEY
        )
        current_answer = extract_content(gen_response)
    except Exception as e:
        return CETIResponse(
            authorization="DENIED",
            response_content="Authorization denied — oracle instability.",
            scope=None,
            refusal_diagnostics=RefusalDiagnostics(
                failure_type="instability",
                details=str(e),
                requirements_for_certification="Retry later."
            ),
            certification_id=None,
            meta={"query": query}
        )

    transcript = [current_answer]
    consensus_reached = False
    rounds_completed = 0

    for round_num in range(1, MAX_ROUNDS_DEFAULT+1):
        rounds_completed = round_num
        critic_system = select_critic_variant()
        critic_prompt = f"""
{critic_system}

Original query: {query}

Proposed answer:
{current_answer}

VERDICT: ACCEPT only if the answer is PERFECT — zero flaws, ambiguities, risks, or gaps.
Otherwise VERDICT: REJECT followed by exhaustive destruction of every issue.
"""
        try:
            critic_response = await acompletion(
                model=CRITIC_MODEL,
                messages=[{"role":"system","content":critic_prompt}],
                max_tokens=400,
                api_key=GROQ_API_KEY
            )
            critique = extract_content(critic_response)
        except Exception:
            critique = "CRITIC FAILURE - VERDICT: REJECT"

        transcript.append(critique)

        if "VERDICT: ACCEPT" in critique.upper():
            consensus_reached = True
            break

        defense_prompt = f"""
Your previous answer was attacked by a hostile critic:

{critique}

Address every point raised. Provide updated answer to the original query.
"""
        gen_messages.append({"role":"user","content":defense_prompt})
        try:
            defense_response = await acompletion(
                model=GENERATOR_MODEL,
                messages=gen_messages,
                max_tokens=500,
                api_key=GROQ_API_KEY
            )
            current_answer = extract_content(defense_response)
        except Exception:
            current_answer = "DEFENSE FAILURE - previous answer stands"

        gen_messages.append({"role":"assistant","content":current_answer})
        transcript.append(current_answer)

    transcript_hash = hashlib.sha256("\n".join(transcript).encode()).hexdigest()
    record_verdict({"query": query, "answer": current_answer, "hash": transcript_hash})

    if consensus_reached and await quorum_vote(current_answer, query, risk_tier):
        scope = AuthorizationScope(
            context_hash=hashlib.sha256(query.encode()).hexdigest(),
            temporal_bounds=f"valid until {int(time.time())+2592000} (30 days)",
            action_class="informational" if risk_tier in ("LOW","MEDIUM") else "decision_support",
            risk_tier_applied=risk_tier
        )
        certification_id = hashlib.sha256(transcript_hash.encode()).hexdigest()
        return CETIResponse(
            authorization="GRANTED",
            response_content=current_answer,
            scope=scope,
            refusal_diagnostics=None,
            certification_id=certification_id,
            meta={"query": query, "rounds_completed": rounds_completed, "transcript_hash": transcript_hash}
        )

    diagnostics = RefusalDiagnostics(
        failure_type="instability",
        details=f"Failed to reach consensus after {rounds_completed} rounds.",
        requirements_for_certification="Achieve perfect ACCEPT in all rounds and quorum consensus."
    )
    return CETIResponse(
        authorization="DENIED",
        response_content="Authorization denied — output not safe for action.",
        scope=None,
        refusal_diagnostics=diagnostics,
        certification_id=None,
        meta={"query": query, "rounds_completed": rounds_completed, "transcript_hash": transcript_hash}
    )
