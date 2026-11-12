import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from services import get_mongo
from validation import ValidationError, validate

bp = Blueprint("upload", __name__)


def _get_file():
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ValidationError("Aucun fichier reçu (champ « file » attendu)")
    return file


@bp.post("/upload/preview")
def preview():
    try:
        file = _get_file()
        file_type, count, rows = validate(file.filename, file.stream)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"filename": file.filename, "type": file_type, "rows": count, "preview": rows})


@bp.post("/upload")
def upload():
    try:
        file = _get_file()
        file_type, count, _ = validate(file.filename, file.stream)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    stem = secure_filename(file.filename.rsplit(".", 1)[0]) or "logs"
    safe_name = f"{stem}.{file_type}"
    file_id = "f" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:4]
    final_path = os.path.join(current_app.config["UPLOAD_DIR"], f"{file_id}__{safe_name}")
    tmp_path = final_path + ".part"

    file.stream.seek(0)
    file.save(tmp_path)
    os.replace(tmp_path, final_path)  # Logstash ne voit jamais un fichier à moitié écrit

    uploaded_at = datetime.now(timezone.utc)
    size_bytes = os.path.getsize(final_path)
    get_mongo()["files"].insert_one({
        "file_id": file_id, "filename": safe_name, "type": file_type, "size_bytes": size_bytes,
        "status": "queued", "rows_validated": count, "logs_count": None,
        "uploaded_at": uploaded_at, "uploaded_by": None,
    })
    return jsonify({"file_id": file_id, "filename": safe_name, "status": "queued", "rows": count,
                    "size_bytes": size_bytes, "uploaded_at": uploaded_at.isoformat()}), 202