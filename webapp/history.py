from datetime import datetime, timezone

from services import get_mongo

FILTER_KEYS = ("level", "service", "date_from", "date_to")


def extract_search(args):
    """Retourne (texte, filtres) d'une requête, sans les valeurs vides."""
    query = args.get("q", "").strip()
    filters = {}
    for key in FILTER_KEYS:
        value = args.get(key, "").strip()
        if value:
            filters[key] = value.upper() if key == "level" else value
    return query, filters


def record_search(query, filters, results_count, user_id=None):
    if not query and not filters:
        return
    col = get_mongo()["searches"]
    now = datetime.now(timezone.utc)
    last = col.find_one({"user_id": user_id}, sort=[("executed_at", -1)])
    if last and last["query"] == query and last["filters"] == filters:
        col.update_one({"_id": last["_id"]}, {"$set": {"executed_at": now, "results_count": results_count}})
    else:
        col.insert_one({"user_id": user_id, "query": query, "filters": filters,
                        "results_count": results_count, "executed_at": now})


def ensure_indexes():
    get_mongo()["searches"].create_index([("executed_at", -1)])