from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from services import get_es, get_mongo

bp = Blueprint("files", __name__)

INGESTION_TIMEOUT = timedelta(minutes=5)
PENDING = ["queued", "processing"]


def _serialize(doc):
    doc = dict(doc)
    doc.pop("_id", None)
    for key in ("uploaded_at", "indexed_at"):
        if doc.get(key):
            doc[key] = doc[key].isoformat()
    return doc


def refresh_status(doc):
    """Met à jour le statut d'un fichier en comptant ses logs dans Elasticsearch."""
    if doc["status"] not in PENDING:
        return doc
    try:
        count = get_es().count(index="logs-saas-*", query={"term": {"file_id": doc["file_id"]}})["count"]
    except Exception:
        return doc  # Elasticsearch indisponible : on garde le statut actuel
    now = datetime.now(timezone.utc)
    update = None
    if count >= doc["rows_validated"]:
        update = {"status": "indexed", "logs_count": count, "indexed_at": now}
    elif count > 0:
        update = {"status": "processing", "logs_count": count}
    else:
        uploaded_at = doc["uploaded_at"]
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        if now - uploaded_at > INGESTION_TIMEOUT:
            update = {"status": "error", "error": "Aucun log indexé après 5 minutes"}
    if update:
        get_mongo()["files"].update_one({"file_id": doc["file_id"]}, {"$set": update})
        doc.update(update)
    return doc


@bp.get("/api/v1/files")
def list_files():
    files = get_mongo()["files"]
    for doc in files.find({"status": {"$in": PENDING}}):
        refresh_status(doc)

    status = request.args.get("status")
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
    query = {"status": status} if status else {}

    total = files.count_documents(query)
    cursor = files.find(query).sort("uploaded_at", -1).skip((page - 1) * per_page).limit(per_page)
    return jsonify({"items": [_serialize(d) for d in cursor], "total": total, "page": page, "per_page": per_page})


@bp.get("/api/v1/files/<file_id>")
def get_file(file_id):
    doc = get_mongo()["files"].find_one({"file_id": file_id})
    if doc is None:
        return jsonify({"error": "Fichier introuvable"}), 404
    return jsonify(_serialize(refresh_status(doc)))