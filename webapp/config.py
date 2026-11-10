import os


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev")
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/data/logs")
    ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
    MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
    MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_USER = os.getenv("MONGO_USER")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    MONGO_DB = os.getenv("MONGO_DB", "logmonitor")
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))