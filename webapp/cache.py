import hashlib
import json

from services import get_redis

SEARCH_TTL = 60
STATS_TTL = 30
KEYS = ("q", "level", "service", "date_from", "date_to", "page", "per_page", "sort", "order")


def make_key(args):
    normalized = {k: args.get(k, "").strip() for k in KEYS}
    normalized["level"] = normalized["level"].upper()
    digest = hashlib.sha1(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    return "cache:search:" + digest


def get_cached(key):
    try:
        raw = get_redis().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None  # Redis indisponible : on interroge la source


def set_cached(key, payload, ttl):
    try:
        get_redis().setex(key, ttl, json.dumps(payload))
    except Exception:
        pass