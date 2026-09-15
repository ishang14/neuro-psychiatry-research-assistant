from functools import lru_cache

from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient

from app.config import settings
from app.rag.embeddings import get_embeddings


@lru_cache
def get_mongo_client() -> MongoClient:
    return MongoClient(settings.mongodb_uri)


@lru_cache
def get_vectorstore() -> MongoDBAtlasVectorSearch:
    collection = get_mongo_client()[settings.mongodb_db][settings.mongodb_collection]
    return MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=get_embeddings(),
        index_name=settings.mongodb_index_name,
        text_key="text",
        embedding_key="embedding",
    )
