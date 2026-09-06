# AskPDF
AskPDF is a lightweight, open-source chatbot designed to turn your static PDF documents into interactive, conversational knowledge bases. Simply upload your files and start asking questions.

## Features

- Streamlit chat UI with bulk upload (up to 10 PDFs) and one-at-a-time uploads.
- PyMuPDF4LLM extraction of page text, detected tables (Markdown), and image metadata.
- Persistent local storage under `data/` (copied PDFs in `data/documents/`,
  SQLite FTS5 and Chroma indexes in `data/index/`).
- Hybrid lexical + semantic retrieval with reciprocal-rank fusion.
- Conservative ambiguity handling: follow-up clarification is requested instead of guessing.
- PDF-only answers by default. If an answer is not found, AskPDF asks for explicit
  yes/no consent before using Gemini general knowledge.
- Citations include filename, exact one-based page, section, and a local `file://`
  link with a `#page=N` anchor. A download button is provided because browsers
  can restrict local-file links.

## Setup

AskPDF uses free/open-source local components and Google's Gemini free tier for
chat and embeddings.

```bash
git clone <your-copy>
cd AskPDF
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Put a Google AI Studio API key in `.env` as `GOOGLE_API_KEY`, then run:

```bash
streamlit run app.py
```

The first indexing operation downloads/initializes the configured Gemini
embedding model. Documents and indexes remain local in `data/`; this directory
is ignored except for its keep files, so do not put secrets there.

## Configuration

`ASKPDF_CHAT_MODEL` defaults to `gemini-2.0-flash` and
`ASKPDF_EMBEDDING_MODEL` defaults to `models/text-embedding-004`. Chunk size,
overlap, and result count can be adjusted in `.env`. The app never sends PDF
content to a general-knowledge call unless the user explicitly selects **Yes**.

## Development

```bash
python3 -m pytest -q
python3 -m compileall -q askpdf app.py
```

The tests cover section-aware chunking helpers, hybrid rank fusion, scope
decisions, and exact-page citation links.
