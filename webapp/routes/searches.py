from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request

from services import get_mongo

bp = Blueprint("searches", __name__)


def _serialize(doc):
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    if doc.get("executed_at"):
        doc["executed_at"] = doc["executed_at"].isoformat()
    return doc


@bp.get("/api/v1/searches")
def list_searches():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    col = get_mongo()["searches"]
    total = col.count_documents({})
    cursor = col.find().sort("executed_at", -1).skip((page - 1) * per_page).limit(per_page)
    return jsonify({"items": [_serialize(d) for d in cursor], "total": total, "page": page, "per_page": per_page})


@bp.delete("/api/v1/searches/<search_id>")
def delete_search(search_id):
    try:
        oid = ObjectId(search_id)
    except InvalidId:
        return jsonify({"error": "Identifiant invalide"}), 400
    result = get_mongo()["searches"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"error": "Recherche introuvable"}), 404
    return jsonify({"deleted": search_id})


@bp.delete("/api/v1/searches")
def clear_searches():
    result = get_mongo()["searches"].delete_many({})
    return jsonify({"deleted": result.deleted_count})