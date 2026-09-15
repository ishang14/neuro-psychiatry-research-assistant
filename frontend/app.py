import os
import time

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

EXAMPLE_QUESTIONS = [
    "What are the genetic risk factors for schizophrenia?",
    "How does deep brain stimulation help Parkinson's disease?",
    "What's the link between sleep disorders and neurodegenerative disease?",
    "What treatments exist for treatment-resistant depression?",
]

st.set_page_config(page_title="Neuro-Psychiatry Research Assistant", page_icon="🧠", layout="centered")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 860px; }
    .stat-card {
        background: color-mix(in srgb, currentColor 6%, transparent);
        border: 1px solid color-mix(in srgb, currentColor 15%, transparent);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        text-align: center;
    }
    .stat-value { font-size: 1.4rem; font-weight: 700; }
    .stat-label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.04em; }
    .source-card {
        border: 1px solid color-mix(in srgb, currentColor 15%, transparent);
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.5rem;
    }
    .source-pmcid { font-weight: 700; }
    .source-meta { font-size: 0.8rem; opacity: 0.7; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60, show_spinner=False)
def get_stats():
    resp = requests.get(f"{BACKEND_URL}/stats", timeout=5)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=15, show_spinner=False)
def get_health():
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return True, bool(data.get("mongodb_connected"))
    except requests.RequestException:
        return False, False


def ask_backend(question: str, top_k: int) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/query",
            json={"question": question, "top_k": top_k},
            timeout=120,
        )
        resp.raise_for_status()
        return {"ok": True, **resp.json()}
    except requests.ConnectionError:
        return {"ok": False, "error": f"Can't reach the backend at {BACKEND_URL}. Is `uvicorn app.main:app` running?"}
    except requests.Timeout:
        return {"ok": False, "error": "The backend took too long to respond. Try again."}
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            pass
        return {"ok": False, "error": f"Backend error ({exc.response.status_code}): {detail or exc}"}


def render_sources(sources: list[dict]) -> None:
    with st.expander(f"📚 Sources ({len(sources)})"):
        for src in sources:
            st.markdown(
                f"""<div class="source-card">
                    <div class="source-pmcid"><a href="{src['url']}" target="_blank">{src['pmcid']}</a></div>
                    <div>{src['title']}</div>
                    <div class="source-meta">Section: {src['section']}</div>
                </div>""",
                unsafe_allow_html=True,
            )


reachable, mongo_ok = get_health()

with st.sidebar:
    st.header("Status")
    if reachable and mongo_ok:
        st.success("Backend connected")
    elif reachable:
        st.warning("Backend up, MongoDB not connected")
    else:
        st.error("Backend unreachable")
    st.caption(f"API: {BACKEND_URL}")

    st.header("Corpus")
    if reachable:
        try:
            stats = get_stats()
            c1, c2 = st.columns(2)
            c1.markdown(
                f'<div class="stat-card"><div class="stat-value">{stats["total_articles"]}</div>'
                f'<div class="stat-label">Articles</div></div>',
                unsafe_allow_html=True,
            )
            c2.markdown(
                f'<div class="stat-card"><div class="stat-value">{stats["total_chunks"]}</div>'
                f'<div class="stat-label">Chunks</div></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Topic: **{stats['topic']}**")
            st.caption(f"Embeddings: `{stats['embedding_model'].split('/')[-1]}`")
            st.caption(f"LLM: `{stats['llm_model']}`")
        except requests.RequestException:
            st.caption("Stats unavailable")
    else:
        st.caption("Stats unavailable")

    st.header("Settings")
    top_k = st.slider("Sources to retrieve (top_k)", min_value=1, max_value=15, value=5)

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🧠 Neuro-Psychiatry Research Assistant")
st.caption(
    "Ask a question about neurology/psychiatry research. Answers are grounded in PMC Open "
    "Access articles with citations — the model won't answer beyond what the retrieved "
    "passages support."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("**Try one of these:**")
    cols = st.columns(2)
    clicked_example = None
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 2].button(q, use_container_width=True, key=f"example_{i}"):
            clicked_example = q
else:
    clicked_example = None

for message in st.session_state.messages:
    avatar = "🧑" if message["role"] == "user" else "🧠"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message.get("sources"):
            render_sources(message["sources"])
        if message.get("elapsed"):
            st.caption(f"⏱ {message['elapsed']:.1f}s")

question = st.chat_input("Ask a research question...") or clicked_example

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🧠"):
        start = time.time()
        with st.spinner("Retrieving passages and generating answer..."):
            result = ask_backend(question, top_k)
        elapsed = time.time() - start

        if result["ok"]:
            st.markdown(result["answer"])
            sources = result.get("sources", [])
            if sources:
                render_sources(sources)
            st.caption(f"⏱ {elapsed:.1f}s")
            st.session_state.messages.append(
                {"role": "assistant", "content": result["answer"], "sources": sources, "elapsed": elapsed}
            )
        else:
            st.error(result["error"])
            st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {result['error']}"})
