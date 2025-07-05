# Lecture Chat with RAG & Video Integration

A full-stack application enabling interactive, context-aware question answering over lecture videos using Retrieval-Augmented Generation (RAG), OpenAI Whisper, and ChromaDB. Users can upload lecture videos, receive real-time processing status, and chat with an AI assistant that references video timestamps and enables direct video navigation from chat.

---

## Features

- **Video Upload & Processing**: Upload lecture videos, with real-time progress via WebSocket.
- **Audio Extraction & Transcription**: Uses ffmpeg and OpenAI Whisper for accurate transcript generation.
- **RAG Pipeline**: Transcript chunking, OpenAI embedding (text-embedding-3-small), ChromaDB vector search, and GPT-4o mini answer generation.
- **Chat UI**: Modern React chat interface with timestamped, context-aware Q&A.
- **Video Player Integration**: Video.js-based player with clickable timestamps in chat for instant navigation.
- **Session Management**: Tracks lecture sessions, supports multiple lectures, and persists session metadata.
- **Error Handling & Recovery**: Robust error messages, retry logic, and restart capability for failed jobs.
- **Performance Optimizations**: Caching, efficient chunk retrieval, and file/memory management.
- **Responsive UI/UX**: Status indicators, spinners, and mobile-friendly design.

---

## Architecture Overview

- **Backend** (FastAPI, Python):
  - File upload, processing job orchestration, WebSocket status updates
  - Audio extraction (ffmpeg), transcription (OpenAI Whisper)
  - Transcript chunking and embedding (LangChain, ChromaDB)
  - RAG query endpoint: semantic search, context retrieval, GPT-4o mini response
  - Session and job management in `db.json`

- **Frontend** (React, TypeScript, TailwindCSS):
  - Video upload with progress
  - Video.js player with timestamp jump
  - Modular chat components: message, input, window, container
  - Real-time status and spinner indicators
  - Responsive and accessible UI

---

## Setup & Usage

### Prerequisites
- Python 3.10+
- Node.js 18+
- ffmpeg (installed and in PATH)
- OpenAI API key (set in `.env`)

### Backend
```bash
cd backend
pip install -r requirements.txt
# Ensure .env with OPENAI_API_KEY is present
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Usage
1. Upload a lecture video via the frontend.
2. Watch real-time processing steps: uploading, extracting audio, transcribing, chunking, embedding.
3. Once ready, chat with the assistant. Answers reference video timestamps.
4. Click timestamps in chat to jump the video player to the relevant moment.

---

## Main Tech Stack
- **Backend**: FastAPI, ffmpeg-python, openai, chromadb, python-dotenv, LangChain
- **Frontend**: React, TypeScript, TailwindCSS, video.js
- **RAG**: OpenAI Whisper, OpenAI Embeddings (text-embedding-3-small), GPT-4o mini
- **Database**: ChromaDB (local), db.json (sessions/jobs)

---

## How It Works: RAG Pipeline Details

1. **Audio Extraction**
   - Uses `ffmpeg-python` to extract audio from uploaded video files.
2. **Transcription**
   - Converts audio to text using OpenAI Whisper (`whisper-1` model) for high accuracy.
3. **Recursive Chunking**
   - Splits transcripts into overlapping chunks using LangChain's recursive algorithm, preserving sentence boundaries and timestamps.
4. **Embedding Generation**
   - Each chunk is embedded using OpenAI's `text-embedding-3-small` model for semantic search.
5. **Vector Storage**
   - Embeddings and metadata (timestamps, video ID) are stored in ChromaDB for fast retrieval.
6. **Semantic Search**
   - User queries are embedded and matched to transcript chunks via vector similarity search (with caching and scoring).
7. **Response Generation**
   - The most relevant chunks are passed to OpenAI GPT-4o mini, which generates a context-aware answer, referencing video timestamps for precise navigation.
8. **Chat-Video Integration**
   - Timestamps in responses are rendered as clickable links, allowing users to jump directly to relevant moments in the video.

---

## Frontend Processing Progress Sequence

After uploading a video, the frontend displays a real-time progress bar and status updates for each backend processing step. The sequence and labels are as follows:

| Backend Step Key         | UI Step Label                      | When it Appears                   |
|-------------------------|-------------------------------------|-----------------------------------|
| uploading               | Uploading video                     | During file upload                |
| extracting_audio        | Extracting audio                    | After upload, before transcription|
| transcribing_audio      | Transcribing audio                   | During Whisper transcription      |
| chunking_and_embedding  | Chunking & embedding transcript     | During chunking/embedding         |
| done                    | Done                                | Processing complete               |
| error                   | Error (with message)                | On any failure                    |

- The progress bar and step label update in real time via WebSocket messages from the backend.
- If any step fails, the progress bar stops and an error message is shown.
- When processing is complete, the chat interface becomes active and interactive.

---

## Project Status
See `todo.md` for a detailed breakdown of completed and remaining tasks, including:
- End-to-end integration tests
- Demo scenarios and sample data
- Documentation and troubleshooting

---

## License
MIT