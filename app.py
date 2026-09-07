"""Streamlit frontend for the AskPDF FastAPI backend."""

from __future__ import annotations

import os

import requests
import streamlit as st


API_URL = os.getenv("ASKPDF_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="AskPDF", page_icon="📄", layout="wide")
st.title("📄 AskPDF")
st.caption("Ask questions against your PDFs with page-level, section-aware citations.")


def api_request(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=300, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not reach the FastAPI server at {API_URL}. "
            "Start it with `uvicorn askpdf.apps.main:app --reload`."
        ) from exc


if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

with st.sidebar:
    st.header("Upload PDFs")
    uploads = st.file_uploader(
        "Choose one or up to 10 PDF files",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if len(uploads) > 10:
        st.error("Please select no more than 10 PDFs.")
    elif st.button("Index selected PDFs", disabled=not uploads):
        with st.status("Sending PDFs to the backend...", expanded=True) as status:
            try:
                payload = api_request(
                    "POST",
                    "/ingest/file",
                    files=[
                        ("files", (item.name, item.getvalue(), "application/pdf"))
                        for item in uploads
                    ],
                )
                status.update(
                    label=f"Indexed {payload['total_chunks']} chunks",
                    state="complete",
                )
                if payload.get("warning"):
                    st.warning(payload["warning"])
            except RuntimeError as exc:
                status.update(label="Indexing failed", state="error")
                st.error(str(exc))
    st.divider()
    st.info("Answers stay inside your PDFs unless you explicitly choose general knowledge.")


def render_citations(citations: list[dict], message_id: int) -> None:
    if not citations:
        return
    st.markdown("**Sources**")
    seen: set[str] = set()
    for index, citation in enumerate(citations):
        key = f"{citation['document_id']}:{citation['page']}:{citation['section']}"
        if key in seen:
            continue
        seen.add(key)
        url = f"{API_URL}{citation['url']}"
        st.markdown(f"- [{citation['label']}]({url})")
        try:
            pdf = requests.get(
                f"{API_URL}/documents/{citation['document_id']}/file", timeout=60
            )
            pdf.raise_for_status()
            st.download_button(
                f"Download {citation['filename']} (page {citation['page']})",
                data=pdf.content,
                file_name=citation["filename"],
                mime="application/pdf",
                key=f"download-{message_id}-{index}",
            )
        except requests.RequestException:
            st.caption("Download unavailable; use the citation link instead.")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_citations(message.get("citations", []), message["id"])

if question := st.chat_input("Ask a question about your uploaded PDFs..."):
    st.session_state.messages.append(
        {"role": "user", "content": question, "id": len(st.session_state.messages)}
    )
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching your PDFs..."):
            try:
                answer = api_request(
                    "POST",
                    "/chat",
                    json={
                        "message": question,
                        "conversation_id": st.session_state.conversation_id,
                    },
                )
                st.session_state.conversation_id = answer["conversation_id"]
            except RuntimeError as exc:
                st.error(str(exc))
                st.stop()
        st.markdown(answer["answer"])
        render_citations(answer["citations"], len(st.session_state.messages))
        if answer["not_found"]:
            st.session_state.pending_general_question = question
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer["answer"],
                "citations": answer["citations"],
                "id": len(st.session_state.messages),
            }
        )

if st.session_state.get("pending_general_question"):
    st.divider()
    st.warning("This is not in the uploaded PDFs. Use general knowledge instead?")
    yes, no = st.columns(2)
    if yes.button("Yes, use general knowledge", key="general-yes"):
        with st.spinner("Asking Gemini general knowledge..."):
            answer = api_request(
                "POST",
                "/chat",
                json={
                    "message": st.session_state.pending_general_question,
                    "conversation_id": st.session_state.conversation_id,
                    "allow_general_knowledge": True,
                },
            )
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer["answer"],
                "citations": [],
                "id": len(st.session_state.messages),
            }
        )
        del st.session_state.pending_general_question
        st.rerun()
    if no.button("No, stay PDF-only", key="general-no"):
        del st.session_state.pending_general_question
        st.rerun()
