# AskPDF

AskPDF lets you upload PDF files and ask questions about them in plain English.
It shows answers with links to the exact PDF page and section used as evidence.

The project has two small applications:

- **FastAPI backend** (`askpdf/apps/main.py`): receives files, builds the search
  index, answers chat questions, and serves the stored PDFs.
- **Streamlit frontend** (`app.py`): provides the friendly upload and chat screen
  and calls the backend over HTTP.

## Quick start for anyone

You only need Python and a free Google AI Studio key.

### 1. Open a terminal in the project folder

In VS Code, choose **File > Open Folder**, select this AskPDF folder, then choose
**Terminal > New Terminal**.

### 2. Create a private Python environment

Run these commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, use:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install AskPDF

```bash
python -m pip install -r requirements.txt
```

### 4. Add your free Gemini key

Copy the sample settings file:

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` using File Explorer.

Open `.env` and replace this value:

```env
GOOGLE_API_KEY=your_google_ai_studio_key
```

Get a key free from [Google AI Studio](https://aistudio.google.com/apikey).
Keep this key private and never commit `.env`.

### 5. Start the backend

Keep this terminal open and run:

```bash
uvicorn askpdf.apps.main:app --reload
```

The backend is now available at `http://127.0.0.1:8000`.
You can check it in a browser at
[`http://127.0.0.1:8000/health`](http://127.0.0.1:8000/health).
Interactive API documentation is at
[`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs).

### 6. Start the frontend

Open a **second VS Code terminal**, activate the environment again, and run:

```bash
source .venv/bin/activate
streamlit run app.py
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

Open the Streamlit URL shown in the terminal, usually
[`http://localhost:8501`](http://localhost:8501).

### 7. Use AskPDF

1. Select one PDF or up to 10 PDFs in the left sidebar.
2. Click **Index selected PDFs** and wait for indexing to finish.
3. Ask a question in the chat box.
4. Open a source link to jump to the exact page in the PDF.
5. If the answer is not in the PDFs, choose **Yes** only if you want Gemini
   general knowledge. Choosing **No** keeps the answer PDF-only.

## What the main files do

| File | Purpose |
| --- | --- |
| `askpdf/apps/main.py` | FastAPI application and Uvicorn entrypoint |
| `app.py` | Streamlit web interface and backend HTTP client |
| `askpdf/api/` | Thin FastAPI routers, schemas, and shared dependencies |
| `askpdf/api/chat.py` | `/chat` route |
| `askpdf/api/health.py` | `/health` route |
| `askpdf/api/ingestion.py` | `/ingest/file` route |
| `askpdf/api/documents.py` | Stored PDF route used by citations |
| `askpdf/services/` | Endpoint-focused business services |
| `askpdf/services/chat_service.py` | Chat orchestration and response mapping |
| `askpdf/services/ingestion_service.py` | Upload validation and ingestion orchestration |
| `askpdf/services/document_service.py` | Safe stored-PDF lookup and serving |
| `askpdf/service.py` | Coordinates ingestion, retrieval, and answers |
| `askpdf/ingestion.py` | Saves PDFs and extracts text, tables, and image metadata |
| `askpdf/chunking.py` | Splits content by headings and preserves page/section metadata |
| `askpdf/retrieval.py` | Combines keyword search and semantic vector search |
| `askpdf/answering.py` | Creates grounded Gemini responses and citation labels |
| `askpdf/scope.py` | Detects incomplete or ambiguous questions |
| `askpdf/config.py` | Reads `.env` settings and chooses data folders |
| `data/documents/` | Local copies of uploaded PDFs |
| `data/index/` | Persistent SQLite and Chroma search indexes |

## Backend endpoints

The frontend uses these endpoints:

| Method and path | What it does |
| --- | --- |
| `GET /health` | Confirms that the backend is running |
| `POST /ingest/file` | Accepts one to ten PDF files and indexes them |
| `POST /chat` | Answers a question and maintains a conversation ID |
| `GET /documents/{document_id}/file` | Serves a stored PDF for page-linked citations |
| `GET /docs` | Opens FastAPI's interactive API documentation |

For `/chat`, send `message` and optionally reuse the returned
`conversation_id`. Set `allow_general_knowledge` to `true` only after the user
has explicitly agreed to leave the PDF-only scope.

## Libraries used, at a high level

- **FastAPI + Uvicorn** provide the Python backend API and development server.
- **Streamlit** creates the simple browser interface without a separate
  JavaScript application.
- **PyMuPDF4LLM** reads PDF text and formats detected tables for retrieval;
  PyMuPDF also helps inspect page and image information.
- **LangChain** provides the document and model integration pieces.
- **ChromaDB** stores semantic embeddings for meaning-based search.
- **SQLite FTS5** provides fast exact-word and keyword search.
- **Google Gemini** supplies free-tier embeddings and answer generation through
  `langchain-google-genai`.
- **python-dotenv** loads local configuration from `.env`.

The hybrid search combines keyword and semantic results, which helps with both
exact terms such as policy names and natural-language questions.

## Configuration

`.env.example` contains the available settings:

```env
GOOGLE_API_KEY=your_google_ai_studio_key
ASKPDF_API_URL=http://127.0.0.1:8000
ASKPDF_CHAT_MODEL=gemini-2.0-flash
ASKPDF_EMBEDDING_MODEL=models/text-embedding-004
ASKPDF_DATA_DIR=data
ASKPDF_TOP_K=6
ASKPDF_CHUNK_SIZE=1200
ASKPDF_CHUNK_OVERLAP=180
```

Uploaded documents and indexes remain on your computer under `data/` and are
ignored by Git. The backend keeps conversations in memory, so restarting it
starts fresh chat histories while preserving uploaded PDFs and indexes.

## Developer checks

```bash
python -m pytest -q
python -m compileall -q askpdf app.py
```
