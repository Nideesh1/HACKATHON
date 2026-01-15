# RAG Voice Backend

CPU-only local RAG demo with voice interface using FastAPI.

## Requirements

- Python 3.10+
- uv (Python package manager)
- FFmpeg (for Whisper audio processing)

## Setup

```bash
# Install uv if not already installed
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Running the Backend

```bash
cd backend

# Install dependencies and run
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Documents

- `GET /documents` - List all documents
- `GET /documents/{doc_id}` - Get document metadata
- `POST /documents` - Upload a .txt document
- `DELETE /documents/{doc_id}` - Delete a document

### Query

- `POST /query` - Query documents using RAG
  ```json
  {
    "query": "your question here",
    "top_k": 3
  }
  ```

### Voice (WebSocket)

- `WS /ws/voice` - Voice streaming endpoint
  - Send binary WAV audio chunks
  - Send `{"type": "end"}` to process accumulated audio
  - Receives transcription and RAG results

### Health

- `GET /health` - Health check with index stats

## Configuration

Environment variables (prefix with `RAG_`):

- `RAG_WHISPER_MODEL` - Whisper model size (default: "base")
- `RAG_EMBEDDING_MODEL` - Sentence transformer model (default: "all-MiniLM-L6-v2")
- `RAG_CHUNK_SIZE` - Text chunk size (default: 500)
- `RAG_TOP_K` - Number of results to return (default: 3)

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── routers/
│   │   ├── documents.py     # Document endpoints
│   │   ├── query.py         # RAG query endpoint
│   │   └── voice.py         # WebSocket voice endpoint
│   └── services/
│       ├── document_service.py   # Document handling
│       ├── embedding_service.py  # Sentence transformers + FAISS
│       ├── whisper_service.py    # Whisper transcription
│       └── rag_service.py        # RAG retrieval
├── data/
│   ├── documents/           # Uploaded documents
│   └── embeddings/          # FAISS index + metadata
└── pyproject.toml           # Project dependencies
```
