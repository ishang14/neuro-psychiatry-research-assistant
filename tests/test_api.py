from fastapi.testclient import TestClient

import app.api.routes as routes_module
from app.main import app


def test_query_returns_answer_and_sources(monkeypatch):
    def fake_answer_question(question, top_k=None):
        return {
            "answer": "This is a test answer [PMC1234567].",
            "sources": [
                {
                    "pmcid": "PMC1234567",
                    "title": "Test Article",
                    "section": "Results",
                    "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/",
                }
            ],
        }

    monkeypatch.setattr(routes_module, "answer_question", fake_answer_question)

    client = TestClient(app)
    response = client.post("/query", json={"question": "What is X?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "This is a test answer [PMC1234567]."
    assert body["sources"][0]["pmcid"] == "PMC1234567"


def test_query_rejects_empty_question():
    client = TestClient(app)
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 422
