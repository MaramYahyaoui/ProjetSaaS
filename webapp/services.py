import redis
from elasticsearch import Elasticsearch
from pymongo import MongoClient

from config import Config

_es = None
_mongo = None
_redis = None


def get_es():
    global _es
    if _es is None:
        _es = Elasticsearch(Config.ES_HOST, request_timeout=5)
    return _es


def get_mongo():
    global _mongo
    if _mongo is None:
        _mongo = MongoClient(
            host=Config.MONGO_HOST, port=Config.MONGO_PORT,
            username=Config.MONGO_USER, password=Config.MONGO_PASSWORD,
            authSource="admin", serverSelectionTimeoutMS=3000,
        )
    return _mongo[Config.MONGO_DB]


def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT,
                             socket_connect_timeout=3, socket_timeout=3)
    return _redis