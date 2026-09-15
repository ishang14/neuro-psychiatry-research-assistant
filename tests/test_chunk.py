from ingestion.chunk import chunk_records


def test_chunk_records_splits_long_text_and_preserves_metadata():
    long_text = "Sentence about neurology. " * 100
    records = [
        {
            "pmcid": "PMC1234567",
            "title": "A Study of Something",
            "journal": "J Neuro",
            "pub_date": "2023-01-01",
            "section": "Results",
            "text": long_text,
        }
    ]

    docs = chunk_records(records)

    assert len(docs) > 1
    for doc in docs:
        assert doc.metadata["pmcid"] == "PMC1234567"
        assert doc.metadata["section"] == "Results"
        assert doc.metadata["source_url"] == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/"
        assert len(doc.page_content) <= 800


def test_chunk_records_skips_empty_text():
    records = [
        {
            "pmcid": "PMC1",
            "title": "T",
            "journal": "J",
            "pub_date": "",
            "section": "Abstract",
            "text": "",
        }
    ]

    assert chunk_records(records) == []
