# Voice RAG Assistant

A fully local, privacy-first voice assistant with RAG (Retrieval-Augmented Generation) and screen analysis capabilities. Everything runs on your machine - no data leaves your computer.

## Demo

[![Watch Demo](https://img.youtube.com/vi/LsLFA4zvKog/0.jpg)](https://youtu.be/LsLFA4zvKog)

## Features

- **Voice Interface**: Click to speak, silence detection auto-sends when you stop talking
- **Document RAG**: Upload documents and ask questions - the AI searches and answers from your files
- **Screen Analysis**: Say "look at my screen" and the AI analyzes what you're viewing
- **General Chat**: Normal conversation, math, questions - routes intelligently
- **Continuous Conversation**: Speaks answers back and auto-restarts listening
- **100% Local & Private**: All models run locally via Ollama - your data never leaves your machine

## Tech Stack

### Backend (Python/FastAPI)
- **Whisper** (faster-whisper) - Speech-to-text
- **Sentence Transformers** - Document embeddings
- **FAISS** - Vector similarity search
- **Chonkie** - Neural chunking for intelligent document splitting
- **Ollama** - Local LLM inference (Gemma 3, FunctionGemma)

### Frontend (React/Vite)
- WebSocket for real-time voice streaming
- Web Audio API for silence detection
- Screen Capture API for vision features
- Browser Speech Synthesis for TTS

## Prerequisites

- **Python 3.10+** (recommend using [uv](https://github.com/astral-sh/uv))
- **Node.js 18+**
- **Ollama** ([Install Ollama](https://ollama.ai))

## Setup

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Windows:**
Download and run the installer from https://ollama.ai/download/windows

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

Start the Ollama service:
```bash
# macOS/Linux
ollama serve

# Windows: Ollama runs automatically after installation (check system tray)
```

### 2. Pull Required Models

```bash
# Main LLM for chat and RAG (4B parameters, good balance of speed/quality)
ollama pull gemma3:4b

# Function routing model (270M parameters, very fast)
ollama pull functiongemma
```

### 3. Backend Setup

```bash
cd backend

# Using uv (recommended - handles everything automatically)
uv sync

# Or using pip
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

## Running the App

### Terminal 1: Start Ollama (if not running)
```bash
ollama serve
```

### Terminal 2: Start Backend
```bash
cd backend

# macOS (Apple Silicon - fixes OpenMP issue):
OMP_NUM_THREADS=1 uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Linux/Windows:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3: Start Frontend
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
│   │       ├── llm_service.py        # Ollama LLM
│   │       ├── router_service.py     # Intent routing
│   │       └── vision_service.py     # Screen analysis
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

## Privacy & Security

This application is designed with privacy as a core principle:

- **100% Local Processing**: All AI models run on your machine via Ollama
- **No Cloud Services**: No API keys, no external calls, no telemetry
- **Open Source**: Full source code available for audit
- **Your Data Stays Yours**: Documents and conversations never leave your computer

## Troubleshooting

### "Ollama connection failed"
Make sure Ollama is running: `ollama serve`

### Models not found
Pull the required models:
```bash
ollama pull gemma3:4b
ollama pull functiongemma
```

### OpenMP crash on macOS (Apple Silicon)
Run with: `OMP_NUM_THREADS=1 uvicorn ...`

### Screen sharing not working
- Make sure you're using HTTPS or localhost
- Check browser permissions for screen capture

### Microphone not working
- Check browser permissions for microphone access
- Try a different browser (Chrome/Edge recommended)

## License

MIT License - Use freely, modify freely, no warranty.
