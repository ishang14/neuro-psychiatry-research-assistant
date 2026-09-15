from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    pmcid: str
    title: str
    section: str
    url: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class HealthResponse(BaseModel):
    status: str
    mongodb_connected: bool


class StatsResponse(BaseModel):
    total_articles: int
    total_chunks: int
    topic: str
    embedding_model: str
    llm_model: str
