import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

COLUMNS = ["timestamp", "level", "service", "endpoint", "http_method", "status_code",
           "response_time_ms", "client_ip", "user_id", "feature", "query_duration_ms", "message"]
SERVICES = ["api", "web", "db", "auth", "payments"]
ENDPOINTS = ["/api/v1/orders", "/api/v1/users", "/login", "/dashboard", "/search", "/upload", "/api/v1/reports"]
FEATURES = ["export_csv", "search", "dashboard", "upload", "alerts", "billing"]
LEVELS = ["INFO"] * 70 + ["WARNING"] * 15 + ["ERROR"] * 12 + ["CRITICAL"] * 3
STATUS = {"INFO": [200, 201, 204], "WARNING": [400, 404, 429], "ERROR": [500, 502, 503, 504], "CRITICAL": [500, 503]}
MESSAGES = {
    "INFO": ["Requête traitée avec succès", "Session utilisateur ouverte"],
    "WARNING": ["Temps de réponse élevé", "Ressource introuvable"],
    "ERROR": ["Timeout lors de l'appel au service", "Connexion à la base refusée"],
    "CRITICAL": ["Service de paiement indisponible", "Pool de connexions épuisé"],
}


def make_row(fake, ts):
    level = random.choice(LEVELS)
    service = random.choice(SERVICES)
    if level == "INFO":
        rt = random.lognormvariate(4.8, 0.5)
    elif level == "WARNING":
        rt = random.uniform(800, 2800)
    else:
        rt = random.uniform(2200, 9000)
    query = round(random.uniform(300, 6000), 1) if service == "db" and level != "INFO" else round(random.uniform(1, 80), 1)
    return {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z", "level": level, "service": service,
        "endpoint": random.choice(ENDPOINTS), "http_method": random.choice(["GET", "GET", "POST", "PUT", "DELETE"]),
        "status_code": random.choice(STATUS[level]), "response_time_ms": round(rt, 1), "client_ip": fake.ipv4(),
        "user_id": "u_%04d" % random.randint(1, 300), "feature": random.choice(FEATURES),
        "query_duration_ms": query, "message": random.choice(MESSAGES[level]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=5000)
    ap.add_argument("--file-id", default="f0001")
    ap.add_argument("--out", default="data/logs")
    args = ap.parse_args()

    fake = Faker()
    now = datetime.now(timezone.utc)
    stamps = sorted(now - timedelta(seconds=random.uniform(0, 86400)) for _ in range(args.rows))
    rows = [make_row(fake, ts) for ts in stamps]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with (out / f"{args.file_id}__saas_logs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with (out / f"{args.file_id}j__saas_logs.json").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} logs écrits dans {out}")


if __name__ == "__main__":
    main()