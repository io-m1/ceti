import os
import requests

def browse_web(query, num_results=5):
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return ""

    payload = {
        "q": query,
        "num": num_results,
        "hl": "en",
        "gl": "us"
    }

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        snippets = []

        for item in data.get("organic", []):
            text = item.get("snippet")
            if text:
                snippets.append(text)

        return "\n".join(snippets[:num_results])
    except Exception:
        return ""
