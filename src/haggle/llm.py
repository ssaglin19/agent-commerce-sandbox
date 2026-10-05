"""Optional LLM hook. With no API key set, bots use scripted lines (mock mode)."""
import json, os, urllib.request

def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))

def complete(system, prompt, max_tokens=120):
    """Return text from Anthropic Messages API, or None if no key / error."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": os.environ.get("HAGGLE_MODEL", "claude-3-5-haiku-latest"),
                       "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
        {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)["content"][0]["text"].strip()
    except Exception:
        return None
