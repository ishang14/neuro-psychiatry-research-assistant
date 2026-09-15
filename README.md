# Neuro-Psychiatry Research Assistant

Ask a neurology/psychiatry research question and get an answer synthesized from PMC Open
Access articles, with citations back to source passages.

**Stack:** Python, LangChain, MongoDB Atlas Vector Search, Hugging Face sentence-transformers
embeddings (biomedical PubMedBERT model), Groq API (free tier), FastAPI.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:
- `MONGODB_URI` — your Atlas connection string.
- `GROQ_API_KEY` — free API key from [console.groq.com/keys](https://console.groq.com/keys) (no credit card required).
- `LLM_MODEL` — defaults to `openai/gpt-oss-120b` (Groq's free tier; 131K context). `openai/gpt-oss-20b` is a faster/lighter free-tier alternative if you hit rate limits.
- `PMC_TOPIC_QUERY` / `PMC_MAX_ARTICLES` — the ingestion topic and cap (defaults to "Neurology and Psychiatry", 800 articles — see the storage note below).

## 1. Ingest a small sample first

```bash
python -m ingestion.load_to_mongo --topic "Neurology and Psychiatry" --max-articles 50
```

This fetches OA articles matching the topic from NCBI, parses the JATS XML, chunks each
section, embeds the chunks, and stores them in your Atlas collection. It's resumable — rerunning
skips PMCIDs already ingested.

## 2. Create the vector search index

```bash
python -m scripts.create_vector_index
```

Attempts to create the index via the driver; if your cluster tier doesn't support that, it
prints the index JSON to paste into the Atlas UI (Search > Create Search Index > JSON Editor).
Wait for the index to finish building in Atlas before querying (usually under a minute for a
small collection).

## 3. Run the API

```bash
uvicorn app.main:app --reload
```

- `GET /health` — checks Mongo connectivity.
- `POST /query` — `{"question": "...", "top_k": 5}` → `{"answer": "...", "sources": [...]}`

Try it:

```bash
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" ^
  -d "{\"question\": \"What biomarkers have been studied for early detection of Alzheimer's disease?\"}"
```

## 4. Scale up ingestion

Once the small sample works end-to-end, rerun step 1 with a higher `--max-articles` (up to
`PMC_MAX_ARTICLES`) to build out the full topic subset.

**Storage note:** MongoDB Atlas's M0 free tier caps out at 512 MB. Observed usage is roughly
0.47 MB per article (~50 chunks/article at 768-dim embeddings), so ~800 articles (~375 MB) stays
safely within the free tier, and ~1000 articles is close to the hard limit. To ingest more than
that, upgrade to a paid Atlas tier (M10+).

## 5. Run the frontend

With the API running (step 3), in a second terminal:

```bash
streamlit run frontend/app.py
```

Opens a chat UI at `http://localhost:8501`. It calls the backend at `BACKEND_URL`
(defaults to `http://127.0.0.1:8000`; set the env var to point elsewhere).

## Deployment

MongoDB Atlas and Groq are already cloud services — only the FastAPI backend and Streamlit
frontend need hosting.

**Backend on Render (free tier):**
1. Push this repo to GitHub.
2. In Render, "New +" → "Blueprint", connect the repo — it reads `render.yaml` automatically.
3. Render prompts for the `sync: false` secrets (`MONGODB_URI`, `GROQ_API_KEY`, `NCBI_API_EMAIL`) — paste your real values there, not into the repo.
4. Note the resulting public URL (`https://<name>.onrender.com`).

⚠️ **Known risk:** Render's free web service tier has historically been capped at 512 MB RAM.
The PubMedBERT embedding model + PyTorch may be tight against that limit — if the deploy
crashes/OOMs, the fix is switching `EMBEDDING_MODEL_NAME` to a smaller model (e.g.
`sentence-transformers/all-MiniLM-L6-v2`, ~90 MB) or upgrading to Render's paid Starter tier.
Free services also sleep after 15 min of inactivity (~1 min cold start on the next request).

**Frontend on Streamlit Community Cloud (free):**
1. On [share.streamlit.io](https://share.streamlit.io), "New app", pick this repo, set the main
   file path to `frontend/app.py`.
2. In the app's "Secrets" settings, add `BACKEND_URL = "https://<your-render-app>.onrender.com"`.
3. Deploy — Streamlit Cloud installs from `frontend/requirements.txt` automatically since it
   sits next to the app file.

## Tests

```bash
pytest tests/
```

## Project layout

- `app/` — FastAPI backend (config, API routes, RAG chain: retrieval + prompt + Groq LLM).
- `ingestion/` — PMC OA fetch, JATS XML parsing, chunking, embed-and-load orchestration.
- `scripts/` — one-off setup scripts (vector index creation).
- `frontend/` — Streamlit chat UI.
- `tests/` — unit tests for chunking and an API smoke test.
