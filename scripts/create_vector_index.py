"""Create the Atlas Vector Search index on the article chunks collection.

Usage:
    python -m scripts.create_vector_index
"""

import json

from pymongo.errors import CollectionInvalid
from pymongo.operations import SearchIndexModel

from app.config import settings
from app.rag.embeddings import get_embeddings
from app.rag.vectorstore import get_mongo_client


def main() -> None:
    db = get_mongo_client()[settings.mongodb_db]
    try:
        db.create_collection(settings.mongodb_collection)
    except CollectionInvalid:
        pass  # already exists

    collection = db[settings.mongodb_collection]
    collection.create_index("pmcid")  # speeds up distinct("pmcid") used by resumability + /stats
    dims = len(get_embeddings().embed_query("dimension probe"))

    definition = {
        "fields": [
            {"type": "vector", "path": "embedding", "numDimensions": dims, "similarity": "cosine"},
        ]
    }

    try:
        model = SearchIndexModel(definition=definition, name=settings.mongodb_index_name, type="vectorSearch")
        collection.create_search_index(model=model)
        print(
            f"Created vector search index '{settings.mongodb_index_name}' on "
            f"{settings.mongodb_db}.{settings.mongodb_collection} ({dims} dims). "
            "It may take a minute to finish building in Atlas."
        )
    except Exception as exc:
        print(f"Could not create the index programmatically ({exc}).")
        print("Create it manually instead: Atlas UI -> your cluster -> Search -> Create Search Index -> JSON Editor")
        print(f"Collection: {settings.mongodb_db}.{settings.mongodb_collection}")
        print(f"Index name: {settings.mongodb_index_name}")
        print("Definition:")
        print(json.dumps(definition, indent=2))


if __name__ == "__main__":
    main()
