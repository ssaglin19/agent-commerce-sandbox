"""Optional model hook. No credentials means bots and judge use scripted lines (mock mode).

Providers, first match wins:
  1. Google Vertex AI (Gemini) via a service account: GOOGLE_SA_JSON (the JSON text) or GOOGLE_APPLICATION_CREDENTIALS (a file path).
     Project comes from GOOGLE_CLOUD_PROJECT or the key's own project_id.
  2. Anthropic: ANTHROPIC_API_KEY
Keys come from the environment only. Nothing is stored in the repo.
Spend caps: HAGGLE_MAX_LLM_CALLS per process (default 40) and HAGGLE_MAX_LLM_CALLS_PER_DAY (default 300, counted per UTC day
in this process; a restart resets it, so it is a guard rail, not a billing control). Past a cap, or on any error, scripted mode.
"""
import base64, json, os, subprocess, tempfile, time, urllib.parse, urllib.request

_calls = 0
_day = {"d": None, "n": 0}
STATS = {"ok": 0}
_tok = {"v": None, "exp": 0}
LAST = {"provider": None}

def _sa():
    raw = os.environ.get("GOOGLE_SA_JSON")
    if raw:
        raw = raw.strip()
        if not raw.startswith("{"): raw = "{" + raw + "}"  # tolerate a key pasted without its outer braces
        return json.loads(raw)
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path:
        with open(path) as f: return json.load(f)
    return None

def _provider():
    if os.environ.get("GOOGLE_SA_JSON") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return "vertex"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None

def available():
    return _provider() is not None

def provider():
    return _provider() or "scripted"

def _b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=")

def _token():
    """OAuth access token from a service-account key. RS256 signing via openssl (no extra packages)."""
    if _tok["v"] and time.time() < _tok["exp"] - 60: return _tok["v"]
    sa = _sa()
    now = int(time.time()); tok_uri = os.environ.get("HAGGLE_TOKEN_URL", sa.get("token_uri", "https://oauth2.googleapis.com/token"))
    claim = {"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/cloud-platform",
             "aud": tok_uri, "iat": now, "exp": now + 3600}
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    unsigned = head + b"." + _b64(json.dumps(claim).encode())
    with tempfile.NamedTemporaryFile("w", suffix=".pem") as kf:
        kf.write(sa["private_key"]); kf.flush()
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", kf.name], input=unsigned,
                             capture_output=True, check=True, timeout=10).stdout
    jwt = (unsigned + b"." + _b64(sig)).decode()
    data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}).encode()
    with urllib.request.urlopen(urllib.request.Request(tok_uri, data), timeout=15) as r:
        j = json.load(r)
    _tok["v"], _tok["exp"] = j["access_token"], now + int(j.get("expires_in", 3600))
    return _tok["v"]

def _vertex(system, prompt, max_tokens):
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or _sa()["project_id"]; model = os.environ.get("HAGGLE_MODEL", "gemini-3.5-flash-lite")
    url = os.environ.get("HAGGLE_VERTEX_URL") or (
        f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/global/publishers/google/models/{model}:generateContent")
    body = json.dumps({"systemInstruction": {"parts": [{"text": system}]},
                       "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                       "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.9}}).encode()
    req = urllib.request.Request(url, body, {"Authorization": "Bearer " + _token(), "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)
    return "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"]).strip()

def _anthropic(system, prompt, max_tokens):
    body = json.dumps({"model": os.environ.get("HAGGLE_MODEL", "claude-3-5-haiku-latest"),
                       "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
        {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["content"][0]["text"].strip()

def complete(system, prompt, max_tokens=120):
    """Return model text, or None (no credentials, call cap reached, or any error)."""
    global _calls
    p = _provider()
    if not p or _calls >= int(os.environ.get("HAGGLE_MAX_LLM_CALLS", "40")):
        return None
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _day["d"] != today: _day.update(d=today, n=0)
    if _day["n"] >= int(os.environ.get("HAGGLE_MAX_LLM_CALLS_PER_DAY", "300")):
        return None
    _calls += 1; _day["n"] += 1
    try:
        text = (_vertex if p == "vertex" else _anthropic)(system, prompt, max_tokens)
        LAST["provider"] = p
        if text: STATS["ok"] += 1
        return text or None
    except Exception as e:
        code = getattr(e, "code", "")
        detail = ""
        if code and hasattr(e, "read"):
            try: detail = str(json.loads(e.read()).get("error", {}).get("status", ""))
            except Exception: pass
        LAST["err"] = (type(e).__name__ + " " + str(code) + " " + detail).strip()
        return None
