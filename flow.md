# System Flow: Lecture RAG Chat

This document describes what happens in the background for key user actions, which APIs and functions are called, and visualizes the flow with both arrow diagrams and a Mermaid flowchart.

---

## 1. Video Upload & Processing Pipeline

**User Action:** Uploads a lecture video via the frontend.

### Step-by-step (with API and function calls)

1. **Frontend**: User selects video → `POST /upload` (FastAPI)
2. **Backend**: `upload_file` endpoint
    - Saves file
    - Calls `cleanup_sessions()` and `create_session()`
    - Adds background job: `process_job(filename)`
3. **Backend**: `process_job(filename)`
    - Calls `notify_progress()` (WebSocket, step="uploading")
    - Extracts audio: `ffmpeg-python` → `notify_progress()` (step="extracting_audio")
    - Transcribes audio: `openai.Audio.transcribe` (Whisper) → `notify_progress()` (step="transcribing_audio")
    - Chunks transcript: `process_transcript(filename)` (LangChain) → `notify_progress()` (step="chunking_and_embedding")
    - Embeds chunks: `OpenAIEmbeddings(model='text-embedding-3-small')`
    - Stores in ChromaDB
    - Final progress: `notify_progress()` (step="done")
4. **Frontend**: Receives progress/status via WebSocket and updates UI (spinners, progress, step names)

### Arrow Diagram

Frontend Upload → `/upload` → `upload_file` → `process_job` →
  ├─ ffmpeg-python (audio extraction)
  ├─ openai.Audio.transcribe (Whisper)
  ├─ process_transcript (chunking)
  ├─ OpenAIEmbeddings (embedding)
  └─ ChromaDB (vector store)
→ WebSocket notify_progress → Frontend UI

---

## 2. Chat Question & RAG Pipeline

**User Action:** User sends a chat question.

### Step-by-step (with API and function calls)

1. **Frontend**: User types question → `POST /rag_query` (FastAPI)
2. **Backend**: `/rag_query` endpoint
    - Calls `Chroma.similarity_search_with_score` (vector search, cache)
    - Retrieves top transcript chunks
    - Calls OpenAI GPT-4o mini for answer
    - Returns answer with timestamp references
3. **Frontend**: Displays answer in chat
    - Clickable timestamps trigger `VideoPlayer.seekTo()`

### Arrow Diagram

Frontend Chat → `/rag_query` → `Chroma.similarity_search_with_score` → GPT-4o mini → Answer → Frontend Chat

---

## 3. Mermaid Flowchart

```mermaid
flowchart TD
    subgraph Upload
        A[User Uploads Video] --> B[POST /upload]
        B --> C[upload_file]
        C --> D[process_job]
        D --> E[ffmpeg-python: Extract Audio]
        E --> F[openai.Audio.transcribe: Whisper]
        F --> G[process_transcript: Chunking]
        G --> H[OpenAIEmbeddings: text-embedding-3-small]
        H --> I[ChromaDB: Store Embeddings]
        I --> J[notify_progress (WebSocket)]
        J --> K[Frontend Progress UI]
    end
    subgraph Chat
        L[User Sends Question] --> M[POST /rag_query]
        M --> N[ChromaDB: Semantic Search]
        N --> O[OpenAI GPT-4o mini: Response]
        O --> P[Answer with Timestamps]
        P --> Q[Frontend Chat UI]
        Q --> R{Timestamp Clicked?}
        R -- Yes --> S[VideoPlayer.seekTo()]
    end
```

---

**Notes for Mermaid:**
- Avoid using unsupported syntax (e.g., no inline HTML, no complex styling, keep node names short and clear).
- Use only standard flowchart elements (nodes, arrows, subgraphs).
- Keep the diagram readable and not overly complex.

---

This flow covers all major user interactions, backend processing, and the RAG pipeline with clear references to APIs and functions at each step.
