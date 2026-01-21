import re

DISALLOWED_PATTERNS = [
    r"(?i)ignore.*(rules|instructions|previous)",
    r"(?i)jailbreak|dan|system prompt|developer mode",
    r"(?i)forget.*(all|previous)",
    r"(?i)simulate.*(bypass|override)",
    r"(?i)you are now|act as",
]

MAX_QUERY_LENGTH = 2000

def is_gaming_attempt(query: str) -> tuple[bool, str | None]:
    if len(query) > MAX_QUERY_LENGTH:
        return True, "Query exceeds maximum length (2000 chars)."

    for pattern in DISALLOWED_PATTERNS:
        if re.search(pattern, query):
            return True, f"Disallowed pattern detected: {pattern}"

    return False, None
