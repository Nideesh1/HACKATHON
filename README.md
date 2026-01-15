# Voice RAG Assistant

A fully local, privacy-first voice assistant with RAG (Retrieval-Augmented Generation) and screen analysis capabilities. Everything runs on your machine - no data leaves your computer.

## Features

- **Voice Interface**: Click to speak, silence detection auto-sends when you stop talking
- **Document RAG**: Upload documents and ask questions - the AI searches and answers from your files
- **Screen Analysis**: Say "look at my screen" and the AI analyzes what you're viewing
- **General Chat**: Normal conversation, math, questions - routes intelligently
- **Continuous Conversation**: Speaks answers back and auto-restarts listening
- **100% Local & Private**: All models run locally from HuggingFace - your data never leaves your machine
- **No Ollama Required**: Uses HuggingFace models directly via llama-cpp-python

## Tech Stack

### Backend (Python/FastAPI)
- **Whisper** (faster-whisper) - Speech-to-text
- **Sentence Transformers** - Document embeddings
- **FAISS** - Vector similarity search
- **Chonkie** - Neural chunking for intelligent document splitting
- **Gemma 3 4B** (GGUF) - Local LLM for chat, RAG, and vision
- **FunctionGemma** - Intent routing/function calling

### Frontend (React/Vite)
- WebSocket for real-time voice streaming
- Web Audio API for silence detection
- Screen Capture API for vision features
- Browser Speech Synthesis for TTS

## Prerequisites

- **Python 3.10+** (recommend using [uv](https://github.com/astral-sh/uv))
- **Node.js 18+**
- **~3GB disk space** for AI models (downloaded automatically on first run)

## Setup

### 1. Install uv (Python package manager)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies (handles everything automatically)
uv sync
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. HuggingFace Access (Required for Gemma models)

Gemma models require accepting Google's license and setting up a token:

1. Create a HuggingFace account at https://huggingface.co
2. Go to https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf and click "Agree and access repository"
3. Go to https://huggingface.co/google/functiongemma-270m-it and click "Agree and access repository"
4. Create an access token at https://huggingface.co/settings/tokens (select "Read" permission)
5. Set up your token in the backend:

```bash
cd backend
cp .env.example .env
# Edit .env and replace 'your_huggingface_token_here' with your actual token
```

Your `.env` file should look like:
```
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Running the App

### Terminal 1: Start Backend
```bash
cd backend

# macOS (Apple Silicon - fixes OpenMP issue):
OMP_NUM_THREADS=1 uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Linux/Windows:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**First run will download models (~3GB total):**
- Gemma 3 4B GGUF (~2.5GB) - for chat, RAG, and vision
- FunctionGemma 270M (~500MB) - for intent routing

### Terminal 2: Start Frontend
```bash
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

## Usage

### Upload Documents
1. Go to the **Documents** page
2. Click "Upload" and select `.txt` files
3. Documents are chunked and indexed automatically

### Voice Queries
1. Go to the **Dashboard** page
2. Allow microphone and screen sharing when prompted
3. Click the microphone button to start listening
4. Speak your question:
   - **"What claims were denied?"** - Searches your documents
   - **"Look at my screen"** - Analyzes what's on your display
   - **"What's 2 plus 2?"** - General chat (no document search)
5. The AI speaks the answer and auto-restarts listening
6. Click again to stop the conversation

### Voice Commands
| Say this... | It does... |
|-------------|------------|
| "search my documents for..." | RAG search |
| "in my files..." | RAG search |
| "which claims..." | RAG search |
| "look at my screen" | Screen capture + vision |
| "what do you see" | Screen capture + vision |
| "what's on my display" | Screen capture + vision |
| Anything else | General conversation |

## Project Structure

```
├── backend/
│   ├── .env.example             # HuggingFace token template
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── routers/
│   │   │   ├── documents.py     # Upload/delete docs
│   │   │   ├── voice.py         # WebSocket for voice
│   │   │   └── query.py         # REST query endpoint
│   │   └── services/
│   │       ├── whisper_service.py    # Speech-to-text
│   │       ├── embedding_service.py  # Vector embeddings
│   │       ├── document_service.py   # Chunking & indexing
│   │       ├── rag_service.py        # RAG pipeline
│   │       ├── llm_service.py        # Gemma 3 GGUF inference
│   │       ├── router_service.py     # FunctionGemma routing
│   │       ├── vision_service.py     # Screen analysis
│   │       └── model_downloader.py   # HuggingFace model download
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Voice interface
│   │   │   └── Documents.jsx    # File management
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
└── README.md
```

## Models Used

| Model | Size | Purpose | Source |
|-------|------|---------|--------|
| Gemma 3 4B (GGUF Q4) | ~2.5GB | Chat, RAG, Vision | [google/gemma-3-4b-it-qat-q4_0-gguf](https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf) |
| FunctionGemma 270M | ~500MB | Intent routing | [google/functiongemma-270m-it](https://huggingface.co/google/functiongemma-270m-it) |
| Whisper Base | ~150MB | Speech-to-text | faster-whisper |
| all-MiniLM-L6-v2 | ~90MB | Document embeddings | sentence-transformers |

## Privacy & Security

This application is designed with privacy as a core principle:

- **100% Local Processing**: All AI models run on your machine
- **No Cloud Services**: No API keys, no external calls, no telemetry
- **No Ollama Required**: Direct HuggingFace model loading
- **Open Source**: Full source code available for audit
- **Your Data Stays Yours**: Documents and conversations never leave your computer

## Troubleshooting

### "Model download failed" or "Access denied"
Make sure you:
1. Accepted the Gemma license on HuggingFace (both models)
2. Created a valid HuggingFace token with "Read" permission
3. Set `HF_TOKEN` in `backend/.env` file

### OpenMP crash on macOS (Apple Silicon)
Run with: `OMP_NUM_THREADS=1 uv run uvicorn ...`

### Screen sharing not working
- Make sure you're using HTTPS or localhost
- Check browser permissions for screen capture

### Microphone not working
- Check browser permissions for microphone access
- Try a different browser (Chrome/Edge recommended)

### Out of memory
- The 4B model needs ~4GB RAM
- Close other applications
- Try reducing `llm_context_size` in config.py

## Configuration

Environment variables (prefix with `RAG_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_LLM_THREADS` | 4 | CPU threads for inference |
| `RAG_LLM_CONTEXT_SIZE` | 4096 | Max context window |
| `RAG_TOP_K` | 5 | Number of chunks to retrieve |

## License

MIT License - Use freely, modify freely, no warranty.
