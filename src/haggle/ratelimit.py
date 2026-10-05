"""Tiny in-memory rate limiter so a public demo cannot hammer the PayPal sandbox."""
import threading, time
_lock, _hits = threading.Lock(), {}
PER_IP, GLOBAL, WINDOW = 6, 40, 60.0   # runs per minute per client, and overall

def allow(key):
    now = time.time()
    with _lock:
        for k in list(_hits):
            _hits[k] = [t for t in _hits[k] if now - t < WINDOW]
            if not _hits[k]: del _hits[k]
        mine, total = len(_hits.get(key, [])), sum(len(v) for v in _hits.values())
        if mine >= PER_IP or total >= GLOBAL: return False
        _hits.setdefault(key, []).append(now); return True
