from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import HealthResponse, QueryRequest, QueryResponse, StatsResponse
from app.rag.chain import answer_question
from app.rag.vectorstore import get_mongo_client

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        get_mongo_client().admin.command("ping")
        connected = True
    except Exception:
        connected = False
    return HealthResponse(status="ok" if connected else "degraded", mongodb_connected=connected)


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    collection = get_mongo_client()[settings.mongodb_db][settings.mongodb_collection]
    return StatsResponse(
        total_articles=len(collection.distinct("pmcid")),
        total_chunks=collection.estimated_document_count(),
        topic=settings.pmc_topic_query,
        embedding_model=settings.embedding_model_name,
        llm_model=settings.llm_model,
    )


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = answer_question(request.question, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return QueryResponse(answer=result["answer"], sources=result["sources"])
