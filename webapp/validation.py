import csv
import json

EXPECTED_COLUMNS = ["timestamp", "level", "service", "endpoint", "http_method", "status_code",
                    "response_time_ms", "client_ip", "user_id", "feature", "query_duration_ms", "message"]
REQUIRED_JSON_FIELDS = {"timestamp", "level", "service"}
ALLOWED_TYPES = {"csv", "json"}
PREVIEW_LINES = 10


class ValidationError(Exception):
    """Fichier refusé : le message est affiché tel quel à l'utilisateur."""


def file_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _lines(stream):
    for raw in stream:
        yield raw.decode("utf-8-sig")


def _validate_csv(stream):
    reader = csv.reader(_lines(stream))
    try:
        header = next(reader)
    except StopIteration:
        raise ValidationError("Le fichier CSV est vide")
    if header != EXPECTED_COLUMNS:
        raise ValidationError("En-tête CSV invalide. Colonnes attendues : " + ", ".join(EXPECTED_COLUMNS))
    preview, count = [], 0
    for line_no, row in enumerate(reader, start=2):
        if len(row) != len(EXPECTED_COLUMNS):
            raise ValidationError(f"Ligne {line_no} : {len(row)} colonnes au lieu de {len(EXPECTED_COLUMNS)}")
        count += 1
        if count <= PREVIEW_LINES:
            preview.append(dict(zip(EXPECTED_COLUMNS, row)))
    if count == 0:
        raise ValidationError("Le fichier CSV ne contient aucune ligne de données")
    return count, preview


def _validate_json(stream):
    preview, count = [], 0
    for line_no, line in enumerate(_lines(stream), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            raise ValidationError(f"Ligne {line_no} : JSON invalide (un objet JSON par ligne est attendu)")
        if not isinstance(obj, dict):
            raise ValidationError(f"Ligne {line_no} : un objet JSON est attendu")
        missing = REQUIRED_JSON_FIELDS - obj.keys()
        if missing:
            raise ValidationError(f"Ligne {line_no} : champs manquants : " + ", ".join(sorted(missing)))
        count += 1
        if count <= PREVIEW_LINES:
            preview.append(obj)
    if count == 0:
        raise ValidationError("Le fichier JSON ne contient aucune ligne")
    return count, preview


def validate(filename, stream):
    """Retourne (type, nombre de lignes, aperçu) ou lève ValidationError."""
    file_type = file_extension(filename)
    if file_type not in ALLOWED_TYPES:
        raise ValidationError("Format non supporté : utilisez un fichier .csv ou .json")
    try:
        count, preview = _validate_csv(stream) if file_type == "csv" else _validate_json(stream)
    except UnicodeDecodeError:
        raise ValidationError("Le fichier doit être encodé en UTF-8")
    return file_type, count, preview