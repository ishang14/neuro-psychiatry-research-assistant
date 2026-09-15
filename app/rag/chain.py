from functools import lru_cache

from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.models.schemas import SourceChunk
from app.rag.vectorstore import get_vectorstore

SYSTEM_PROMPT = """You are a biomedical research assistant. Answer the user's question using ONLY \
the provided context passages from PMC Open Access articles. Every factual claim must be followed \
by a citation to the source passage's PMCID, e.g. "Amyloid-beta accumulation precedes cognitive \
decline [PMC1234567]." If the context does not contain enough information to answer the question, \
say so explicitly instead of guessing. Use only plain ASCII punctuation (hyphens, straight quotes) \
- do not use em dashes, en dashes, or curly/smart quotes."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


@lru_cache
def get_llm() -> ChatGroq:
    return ChatGroq(model=settings.llm_model, api_key=settings.groq_api_key)


def _format_docs(docs: list[Document]) -> str:
    return "\n\n".join(
        f"[{d.metadata.get('pmcid', 'unknown')} | {d.metadata.get('section', 'unknown')}] {d.page_content}"
        for d in docs
    )


def _dedupe_sources(docs: list[Document]) -> list[SourceChunk]:
    seen: set[tuple[str, str]] = set()
    sources: list[SourceChunk] = []
    for d in docs:
        pmcid = d.metadata.get("pmcid", "unknown")
        section = d.metadata.get("section", "unknown")
        key = (pmcid, section)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            SourceChunk(
                pmcid=pmcid,
                title=d.metadata.get("title", ""),
                section=section,
                url=d.metadata.get("source_url", f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"),
            )
        )
    return sources


def _sanitize(text: str) -> str:
    # Groq's gpt-oss models occasionally emit a stray U+FFFD in place of an em/en dash
    # (a server-side detokenization quirk); strip it defensively rather than show it to users.
    return text.replace("�", "-")


def answer_question(question: str, top_k: int | None = None) -> dict:
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": top_k or settings.top_k})
    docs = retriever.invoke(question)

    messages = PROMPT.format_messages(context=_format_docs(docs), question=question)
    response = get_llm().invoke(messages)

    return {"answer": _sanitize(response.content), "sources": _dedupe_sources(docs)}
