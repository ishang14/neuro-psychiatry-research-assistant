from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def chunk_records(records: list[dict]) -> list[Document]:
    """Split each section record's text into overlapping chunks, preserving article metadata."""
    docs: list[Document] = []
    for record in records:
        pmcid = record["pmcid"]
        metadata = {
            "pmcid": pmcid,
            "title": record["title"],
            "journal": record["journal"],
            "pub_date": record["pub_date"],
            "section": record["section"],
            "source_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
        }
        for chunk_text in _splitter.split_text(record["text"]):
            docs.append(Document(page_content=chunk_text, metadata=metadata.copy()))
    return docs
