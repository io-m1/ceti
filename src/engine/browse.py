import requests
from src.config.settings import SERPER_API_KEY

def browse_web(query, num_results=5):
    if not SERPER_API_KEY:
        return ""
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": num_results,
        "gl": "us",
        "hl": "en",
    }
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        snippets = [r.get("snippet", "") for r in data.get("organic", []) if r.get("snippet")]
        context = "\n".join(snippets[:num_results])
        return f"Web context (Serper search):\n{context}" if context else "No web context found."
    except Exception as e:
        return f"Web search failed: {str(e)}"
