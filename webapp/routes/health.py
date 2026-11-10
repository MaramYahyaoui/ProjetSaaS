import time

from flask import Blueprint, jsonify

from services import get_es, get_mongo, get_redis

bp = Blueprint("health", __name__)


def _check_es():
    return {"cluster_status": get_es().cluster.health()["status"]}


def _check_mongo():
    get_mongo().client.admin.command("ping")
    return {}


def _check_redis():
    get_redis().ping()
    return {}


@bp.get("/health")
def health():
    services = {}
    for name, check in {"elasticsearch": _check_es, "mongodb": _check_mongo, "redis": _check_redis}.items():
        start = time.perf_counter()
        try:
            services[name] = {"status": "up", **check()}
        except Exception as exc:
            services[name] = {"status": "down", "error": type(exc).__name__}
        services[name]["response_ms"] = round((time.perf_counter() - start) * 1000, 1)
    down = [n for n, s in services.items() if s["status"] == "down"]
    status = "healthy" if not down else ("down" if len(down) == len(services) else "degraded")
    return jsonify({"status": status, "services": services}), (200 if status == "healthy" else 503)