"""Streamlit entrypoint for AskPDF."""

from __future__ import annotations

import streamlit as st

from askpdf.answering import citation_label, pdf_link
from askpdf.config import settings
from askpdf.service import AskPDF


st.set_page_config(page_title="AskPDF", page_icon="📄", layout="wide")
st.title("📄 AskPDF")
st.caption("Ask questions against your PDFs with page-level, section-aware citations.")


@st.cache_resource
def get_service() -> AskPDF:
    return AskPDF(settings)


service = get_service()

with st.sidebar:
    st.header("Upload PDFs")
    st.write("Upload up to 10 PDFs at once, or add one at a time.")
    uploads = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploads",
    )
    if len(uploads) > 10:
        st.error("Please select no more than 10 PDFs.")
    elif st.button("Index selected PDFs", disabled=not uploads):
        with st.status("Extracting and indexing PDFs…", expanded=True) as status:
            try:
                chunks = sum(service.ingest_upload(item) for item in uploads)
                status.update(label=f"Indexed {chunks} chunks", state="complete")
                st.session_state["indexed"] = True
            except Exception as exc:
                status.update(label="Indexing failed", state="error")
                st.error(str(exc))
    st.divider()
    st.info("Default scope is uploaded PDFs only. General knowledge is never used without consent.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("citations"):
            st.markdown("**Sources**")
            for citation in message["citations"]:
                result = citation["result"]
                st.markdown(
                    f"- [{citation['label']}]({citation['url']}) "
                    "(the PDF is also available from the download button below)"
                )
                st.download_button(
                    f"Download {result['filename']} (page {result['page']})",
                    data=open(result["source_path"], "rb").read(),
                    file_name=result["filename"],
                    mime="application/pdf",
                    key=f"download-{result['chunk_id']}-{message['id']}",
                )

if question := st.chat_input("Ask a question about your uploaded PDFs…"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching your PDFs…"):
            try:
                answer = service.ask(question)
            except Exception as exc:
                st.error(f"Unable to answer: {exc}")
                st.stop()
        st.markdown(answer.text)
        citations = []
        if answer.citations:
            st.markdown("**Sources**")
            seen: set[str] = set()
            for result in answer.citations:
                key = f"{result.metadata.get('filename')}:{result.metadata.get('page')}:{result.metadata.get('section')}"
                if key in seen:
                    continue
                seen.add(key)
                label = citation_label(result)
                st.markdown(f"- [{label}]({pdf_link(result)})")
                source_path = result.metadata.get("source_path")
                if source_path:
                    with open(source_path, "rb") as pdf:
                        st.download_button(
                            f"Download {label}",
                            data=pdf.read(),
                            file_name=result.metadata.get("filename", "document.pdf"),
                            mime="application/pdf",
                            key=f"download-live-{key}",
                        )
                citations.append({"label": label, "url": pdf_link(result), "result": {
                    **result.metadata, "source_path": source_path
                }})
        if answer.not_found:
            st.warning("I could not find an answer in the uploaded PDFs.")
            st.session_state["pending_general_question"] = question
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer.text,
            "citations": citations,
            "id": len(st.session_state.messages),
        })

if st.session_state.get("pending_general_question"):
    st.divider()
    question = st.session_state["pending_general_question"]
    st.warning("This is not in the uploaded PDFs. Use general knowledge instead?")
    col_yes, col_no = st.columns(2)
    if col_yes.button("Yes, use general knowledge", key="general-yes"):
        with st.spinner("Asking Gemini general knowledge…"):
            answer = service.ask(question, allow_general_knowledge=True)
        st.session_state.messages.append({"role": "assistant", "content": answer.text, "citations": [], "id": len(st.session_state.messages)})
        del st.session_state["pending_general_question"]
        st.rerun()
    if col_no.button("No, stay PDF-only", key="general-no"):
        del st.session_state["pending_general_question"]
        st.rerun()
