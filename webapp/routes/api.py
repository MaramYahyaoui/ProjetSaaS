import csv
import io
from datetime import datetime, timezone
from cache import STATS_TTL, get_cached, set_cached
from flask import Blueprint, Response, jsonify, request

from routes.search import MAX_WINDOW, build_query
from services import get_es, get_mongo

bp = Blueprint("api", __name__)

INDEX = "logs-saas-*"
EXPORT_FIELDS = ["timestamp", "level", "service", "endpoint", "http_method", "status_code",
                 "response_time_ms", "user_id", "feature", "message", "file_id"]
ERROR_LEVELS = ["ERROR", "CRITICAL"]
SLOW_THRESHOLD_MS = 3000


def _iso(epoch_ms):
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()


def _safe_cell(value):
    """Évite l'injection de formules quand le CSV est ouvert dans Excel."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


@bp.get("/api/v1/stats")
def stats():
    cached = get_cached("cache:stats")
    if cached is not None:
        return jsonify({**cached, "cached": True})
    try:
        res = get_es().search(index=INDEX, size=0, track_total_hits=True, aggs={
            "today": {"filter": {"range": {"@timestamp": {"gte": "now/d"}}}},
            "errors": {"filter": {"terms": {"level": ERROR_LEVELS}}},
            "slow": {"filter": {"range": {"response_time_ms": {"gt": SLOW_THRESHOLD_MS}}}},
            "by_level": {"terms": {"field": "level", "size": 10}},
        })
    except Exception as exc:
        return jsonify({"error": "Statistiques indisponibles", "detail": type(exc).__name__}), 503
    aggs = res.get("aggregations", {})
    try:
        files_total = get_mongo()["files"].count_documents({})
    except Exception:
        files_total = None
    result = {
        "total_logs": res["hits"]["total"]["value"],
        "logs_today": aggs.get("today", {}).get("doc_count", 0),
        "error_logs": aggs.get("errors", {}).get("doc_count", 0),
        "slow_requests": aggs.get("slow", {}).get("doc_count", 0),
        "files_uploaded": files_total,
        "by_level": {b["key"]: b["doc_count"] for b in aggs.get("by_level", {}).get("buckets", [])},
    }
    set_cached("cache:stats", result, STATS_TTL)
    return jsonify({**result, "cached": False})

@bp.get("/api/v1/stats/timeline")
def timeline():
    """Nombre de logs et d'erreurs par heure, sur les N heures qui précèdent le dernier log."""
    hours = min(max(request.args.get("hours", 24, type=int), 1), 168)
    try:
        es = get_es()
        last = es.search(index=INDEX, size=0, aggs={"last": {"max": {"field": "@timestamp"}}})
        end_ms = last.get("aggregations", {}).get("last", {}).get("value")
        if end_ms is None:
            return jsonify({"hours": hours, "end": None, "buckets": []})
        end_ms = int(end_ms)
        start_ms = end_ms - hours * 3600 * 1000
        res = es.search(
            index=INDEX, size=0,
            query={"range": {"@timestamp": {"gte": start_ms, "lte": end_ms, "format": "epoch_millis"}}},
            aggs={"per_hour": {
                "date_histogram": {"field": "@timestamp", "fixed_interval": "1h", "min_doc_count": 0,
                                   "extended_bounds": {"min": start_ms, "max": end_ms}},
                "aggs": {"errors": {"filter": {"terms": {"level": ERROR_LEVELS}}}},
            }},
        )
    except Exception as exc:
        return jsonify({"error": "Statistiques indisponibles", "detail": type(exc).__name__}), 503
    buckets = [{"time": b["key_as_string"], "total": b["doc_count"], "errors": b["errors"]["doc_count"]}
               for b in res["aggregations"]["per_hour"]["buckets"]]
    return jsonify({"hours": hours, "end": _iso(end_ms), "buckets": buckets})


@bp.get("/api/v1/logs/<log_id>")
def log_detail(log_id):
    try:
        res = get_es().search(index=INDEX, query={"ids": {"values": [log_id]}}, size=1)
    except Exception as exc:
        return jsonify({"error": "Recherche impossible", "detail": type(exc).__name__}), 503
    hits = res["hits"]["hits"]
    if not hits:
        return jsonify({"error": "Log introuvable"}), 404
    hit = hits[0]
    source = dict(hit["_source"])
    timestamp = source.get("@timestamp")
    for key in ("@timestamp", "event", "host", "log"):
        source.pop(key, None)
    return jsonify({"id": hit["_id"], "index": hit["_index"], "timestamp": timestamp, **source})

@bp.get("/search/export")
def export_csv():
    try:
        query = build_query(request.args)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    limit = min(max(request.args.get("limit", MAX_WINDOW, type=int), 1), MAX_WINDOW)
    try:
        res = get_es().search(index=INDEX, query=query, sort=[{"@timestamp": {"order": "desc"}}], size=limit,
                              source_includes=["@timestamp"] + EXPORT_FIELDS[1:])
    except Exception as exc:
        return jsonify({"error": "Export impossible", "detail": type(exc).__name__}), 503

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_FIELDS)
    for hit in res["hits"]["hits"]:
        source = hit["_source"]
        row = {**source, "timestamp": source.get("@timestamp")}
        writer.writerow([_safe_cell(row.get(field)) for field in EXPORT_FIELDS])
    name = "logs_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".csv"
    return Response("\ufeff" + buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})