from datetime import datetime

from flask import Blueprint, jsonify, request

from services import get_es

bp = Blueprint("search", __name__)

LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
SORT_FIELDS = {"date": "@timestamp", "level": "level", "service": "service"}
SOURCE_FIELDS = ["@timestamp", "level", "service", "endpoint", "http_method", "status_code",
                 "response_time_ms", "user_id", "feature", "message", "file_id"]
MAX_WINDOW = 10000  # limite d'Elasticsearch pour from + size


def _parse_date(value, name):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{name} invalide : format attendu AAAA-MM-JJ")
    return value


def build_query(args):
    must, filters = [], []
    q = args.get("q", "").strip()
    if q:
        must.append({"match": {"message": {"query": q, "operator": "and"}}})
    level = args.get("level", "").strip().upper()
    if level:
        if level not in LEVELS:
            raise ValueError("level invalide : " + ", ".join(sorted(LEVELS)))
        filters.append({"term": {"level": level}})
    service = args.get("service", "").strip()
    if service:
        filters.append({"term": {"service": service}})
    date_range = {}
    date_from = args.get("date_from", "").strip()
    date_to = args.get("date_to", "").strip()
    if date_from:
        date_range["gte"] = _parse_date(date_from, "date_from") + "||/d"
    if date_to:
        date_range["lte"] = _parse_date(date_to, "date_to") + "||/d"
    if date_range:
        date_range["format"] = "yyyy-MM-dd"
        filters.append({"range": {"@timestamp": date_range}})
    if not must and not filters:
        return {"match_all": {}}
    return {"bool": {"must": must, "filter": filters}}


@bp.get("/search")
def search():
    try:
        query = build_query(request.args)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 100)
    if page * per_page > MAX_WINDOW:
        return jsonify({"error": "Pagination limitée aux 10 000 premiers résultats : affinez votre recherche"}), 400

    sort_key = request.args.get("sort", "date")
    if sort_key not in SORT_FIELDS:
        return jsonify({"error": "sort invalide : " + ", ".join(SORT_FIELDS)}), 400
    order = "asc" if request.args.get("order", "desc") == "asc" else "desc"
    field = SORT_FIELDS[sort_key]
    sort = [{field: {"order": order}}]
    if field != "@timestamp":
        sort.append({"@timestamp": {"order": "desc"}})

    try:
        res = get_es().search(index="logs-saas-*", query=query, sort=sort, from_=(page - 1) * per_page,
                              size=per_page, track_total_hits=True, source_includes=SOURCE_FIELDS)
    except Exception as exc:
        return jsonify({"error": "Recherche impossible", "detail": type(exc).__name__}), 503

    items = []
    for hit in res["hits"]["hits"]:
        source = hit["_source"]
        source["timestamp"] = source.pop("@timestamp", None)
        items.append({"id": hit["_id"], **source})
    return jsonify({"total": res["hits"]["total"]["value"], "page": page, "per_page": per_page, "items": items})