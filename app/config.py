from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongodb_uri: str
    mongodb_db: str = "pmc_rag"
    mongodb_collection: str = "article_chunks"
    mongodb_index_name: str = "vector_index"

    embedding_model_name: str = "NeuML/pubmedbert-base-embeddings"

    groq_api_key: str
    llm_model: str = "openai/gpt-oss-120b"

    top_k: int = 5

    pmc_topic_query: str = "Neurology and Psychiatry"
    pmc_max_articles: int = 800
    ncbi_api_email: str | None = None


settings = Settings()
