import re

disallowed_patterns = [
    r"(?i)ignore.*(rules|instructions|previous)",
    r"(?i)jailbreak|dan|system prompt|you are now",
    r"(?i)forget.*(all|previous)"
]

def is_gaming_attempt(query: str) -> bool:
    if len(query) > 2000:
        return True
    for pattern in disallowed_patterns:
        if re.search(pattern, query):
            return True
    return False
