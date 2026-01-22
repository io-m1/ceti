import os
import requests

def browse_web(query: str, limit: int = 5) -> str:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return ""

    endpoint = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": limit
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        snippets = []
        for item in data.get("organic", []):
            text = item.get("snippet")
            if text:
                snippets.append(text)
        return "\n".join(snippets)
    except Exception:
        return ""
