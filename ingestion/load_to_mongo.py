"""Orchestrate fetch -> parse -> chunk -> embed -> store for a PMC OA topic subset.

Usage:
    python -m ingestion.load_to_mongo --topic "Neurology and Psychiatry" --max-articles 50
"""

import argparse

from tqdm import tqdm

from app.config import settings
from app.rag.vectorstore import get_mongo_client, get_vectorstore
from ingestion.chunk import chunk_records
from ingestion.fetch_pmc import fetch_topic_articles
from ingestion.parse_nxml import parse_nxml


def _already_ingested_pmcids() -> set[str]:
    collection = get_mongo_client()[settings.mongodb_db][settings.mongodb_collection]
    return set(collection.distinct("pmcid"))


def run(topic: str, max_articles: int) -> None:
    vectorstore = get_vectorstore()
    seen = _already_ingested_pmcids()
    print(f"{len(seen)} articles already ingested; skipping those.")

    ingested = 0
    for pmcid, nxml_bytes in tqdm(fetch_topic_articles(topic, max_articles, skip_ids=seen), total=max_articles):
        try:
            records = parse_nxml(nxml_bytes, pmcid)
            docs = chunk_records(records)
            if docs:
                vectorstore.add_documents(docs)
                ingested += 1
        except Exception as exc:
            print(f"Skipping {pmcid}: {exc}")

    print(f"Ingested {ingested} new articles into {settings.mongodb_db}.{settings.mongodb_collection}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default=settings.pmc_topic_query)
    parser.add_argument("--max-articles", type=int, default=settings.pmc_max_articles)
    args = parser.parse_args()
    run(args.topic, args.max_articles)


if __name__ == "__main__":
    main()
