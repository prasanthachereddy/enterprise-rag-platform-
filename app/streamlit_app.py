"""Streamlit page. Start it with: streamlit run app\\streamlit_app.py"""

import streamlit as st

from enterprise_rag.answers.bedrock import AnswerGenerationError
from enterprise_rag.answers.service import ask
from enterprise_rag.config import Settings, get_settings
from enterprise_rag.retrieval.embeddings import LocalEmbedder
from enterprise_rag.retrieval.index import create_client

MODES = ["rerank", "hybrid", "vector", "bm25"]


@st.cache_resource
def load_services() -> tuple[Settings, object, LocalEmbedder]:
    settings = get_settings()
    embedder = LocalEmbedder(
        settings.local_embedding_url,
        settings.local_embedding_model,
        settings.local_embedding_dimensions,
    )
    return settings, create_client(settings.opensearch_url), embedder


st.set_page_config(page_title="Policy Assistant", layout="wide")
st.title("Policy & Operations Knowledge Assistant")
settings, client, embedder = load_services()
mode = st.sidebar.selectbox("Retrieval mode", MODES)
st.sidebar.caption(f"Answer mode: {settings.answer_mode}")
st.sidebar.caption("Synthetic sample documents only.")

question = st.text_input("Ask a question about company policy")
if st.button("Ask") and question.strip():
    try:
        with st.spinner("Searching..."):
            answer = ask(question, settings, client, embedder, mode)
    except ValueError as exc:
        st.warning(str(exc))
    except AnswerGenerationError as exc:
        st.error(f"The model step failed: {exc}. Try again, or set ANSWER_MODE=offline.")
    except Exception as exc:
        st.error(f"Search failed ({type(exc).__name__}). Are both Docker containers running?")
    else:
        if answer.found:
            st.success(answer.text)
        else:
            st.info(answer.text)
        for citation in answer.citations:
            heading = citation.heading or "no heading"
            st.markdown(f"**[{citation.number}]** {citation.source_filename} | {heading}")
            st.caption(citation.snippet)
        with st.expander(f"Retrieved passages ({len(answer.retrieved)})"):
            for result in answer.retrieved:
                st.markdown(
                    f"**{result.rank}.** {result.source_filename} | {result.heading or '-'} "
                    f"(score {result.score:.4f})"
                )
                st.caption(" ".join(result.text.split())[:200])