from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
import json
from typing import List
import ffmpeg
from openai import OpenAI
import os
from dotenv import load_dotenv
import math
from fastapi.websockets import WebSocket
load_dotenv()

app = FastAPI()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Allow CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job queue and WebSocket manager
job_queue = []
websockets: List[WebSocket] = []

# Pydantic models
class RAGQuery(BaseModel):
    video_id: str
    query: str

# --- DATABASE INITIALIZATION ---
def init_db():
    db_path = "db.json"
    if not os.path.exists(db_path):
        with open(db_path, "w") as dbf:
            json.dump({
                "lectures": [],
                "processing_jobs": [],
                "sessions": []
            }, dbf, indent=2)
    else:
        # Ensure all required keys exist
        with open(db_path, "r+") as dbf:
            db = json.load(dbf)
            if "lectures" not in db:
                db["lectures"] = []
            if "processing_jobs" not in db:
                db["processing_jobs"] = []
            if "sessions" not in db:
                db["sessions"] = []
            dbf.seek(0)
            json.dump(db, dbf, indent=2)
            dbf.truncate()

# Initialize database on startup
init_db()

# --- SESSION MANAGEMENT ---
# Each session is a dict: {"session_id": str, "filename": str, "created_at": str, ...}
import uuid
from datetime import datetime

def create_session(filename: str) -> dict:
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "filename": filename,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    db_path = "db.json"
    with open(db_path, "r+") as dbf:
        db = json.load(dbf)
        if "sessions" not in db:
            db["sessions"] = []
        db["sessions"].append(session)
        dbf.seek(0)
        json.dump(db, dbf, indent=2)
        dbf.truncate()
    return session

def cleanup_sessions():
    db_path = "db.json"
    with open(db_path, "r+") as dbf:
        db = json.load(dbf)
        db["sessions"] = []
        dbf.seek(0)
        json.dump(db, dbf, indent=2)
        dbf.truncate()

def get_sessions():
    db_path = "db.json"
    with open(db_path, "r") as dbf:
        db = json.load(dbf)
        return db.get("sessions", [])

async def notify_progress(filename: str, progress: int, step: str = None):
    job_id = filename
    for ws in websockets:
        try:
            await ws.send_json({"filename": job_id, "progress": progress, "step": step})
        except Exception:
            pass

async def chunk_audio_file(audio_path: str, chunk_duration: int = 600) -> List[str]:
    """
    Split audio file into chunks of specified duration (in seconds).
    Default is 10 minutes (600 seconds) to stay well under 25MB limit.
    """
    try:
        # Get audio duration
        probe = ffmpeg.probe(audio_path)
        duration = float(probe['format']['duration'])
        
        # Calculate number of chunks needed
        num_chunks = math.ceil(duration / chunk_duration)
        
        chunk_paths = []
        base_name = os.path.splitext(audio_path)[0]
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = f"{base_name}_chunk_{i:03d}.mp3"
            
            # Create audio chunk
            (
                ffmpeg
                .input(audio_path, ss=start_time, t=chunk_duration)
                .output(chunk_path, acodec='mp3')
                .overwrite_output()
                .run(quiet=True)
            )
            
            chunk_paths.append(chunk_path)
        
        return chunk_paths
        
    except Exception as e:
        print(f"Error chunking audio: {e}")
        return []

async def process_job(filename: str):
    db_path = "db.json"
    video_path = os.path.join("uploads", filename)
    audio_path = os.path.join("uploads", f"{os.path.splitext(filename)[0]}.mp3")
    status = {
        "filename": filename,
        "status": "queued",
        "progress": 0,
        "error": None,
        "audio_path": None
    }
    # Add job to db.json
    try:
        with open(db_path, "r+") as dbf:
            db = json.load(dbf)
            db["processing_jobs"].append(status)
            dbf.seek(0)
            json.dump(db, dbf, indent=2)
            dbf.truncate()
    except Exception as e:
        await notify_progress(filename, 0)
        return
    try:
        await notify_progress(filename, 5, step="uploading")
        # Update status to processing
        with open(db_path, "r+") as dbf:
            db = json.load(dbf)
            for job in db["processing_jobs"]:
                if job["filename"] == filename:
                    job["status"] = "processing"
                    job["progress"] = 5
            dbf.seek(0)
            json.dump(db, dbf, indent=2)
            dbf.truncate()
        # Audio extraction
        await notify_progress(filename, 10, step="extracting_audio")
        try:
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='mp3', vn=None)
                .overwrite_output()
                .run(quiet=True)
            )
            await notify_progress(filename, 30, step="audio_extracted")
        except Exception as e:
            # Error during extraction
            error_msg = f"Audio extraction failed: {str(e)}"
            with open(db_path, "r+") as dbf:
                db = json.load(dbf)
                for job in db["processing_jobs"]:
                    if job["filename"] == filename:
                        job["status"] = "error"
                        job["progress"] = 0
                        job["error"] = error_msg
                dbf.seek(0)
                json.dump(db, dbf, indent=2)
                dbf.truncate()
            await notify_progress(filename, 0)
            return
        
        # Check audio file size and chunk if necessary
        audio_size = os.path.getsize(audio_path)
        max_size = 24 * 1024 * 1024  # 24MB to be safe (OpenAI limit is 25MB)
        
        transcript = ""
        transcript_path = os.path.join("uploads", f"{os.path.splitext(filename)[0]}.transcript.txt")
        
        if audio_size > max_size:
            await notify_progress(filename, 35, step="chunking_large_audio")
            # Split large audio file into chunks
            chunk_duration = 600  # 10 minutes per chunk
            chunk_paths = await chunk_audio_file(audio_path, chunk_duration)
            
            if not chunk_paths:
                error_msg = "Failed to chunk large audio file"
                with open(db_path, "r+") as dbf:
                    db = json.load(dbf)
                    for job in db["processing_jobs"]:
                        if job["filename"] == filename:
                            job["status"] = "error"
                            job["progress"] = 0
                            job["error"] = error_msg
                    dbf.seek(0)
                    json.dump(db, dbf, indent=2)
                    dbf.truncate()
                await notify_progress(filename, 0)
                return
            
            # Process each chunk
            transcript_chunks = []
            total_chunks = len(chunk_paths)
            
            for i, chunk_path in enumerate(chunk_paths):
                max_retries = 3
                chunk_transcript = None
                
                for attempt in range(max_retries):
                    try:
                        progress = 40 + (i * 20) // total_chunks  # Progress from 40% to 60%
                        await notify_progress(filename, progress, step=f"transcribing_chunk_{i+1}_of_{total_chunks}")
                        
                        with open(chunk_path, "rb") as audio_file:
                            whisper_response = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file,
                                response_format="verbose_json",
                                timestamp_granularities=["word"]
                            )
                        chunk_transcript = whisper_response.text
                        
                        # Store detailed transcript with timestamps for this chunk
                        chunk_number = i
                        chunk_start_offset = i * chunk_duration  # Offset for this chunk in the full video
                        detailed_transcript_path = f"{os.path.splitext(transcript_path)[0]}_chunk_{chunk_number:03d}_detailed.json"
                        
                        # Process words and add global timestamps
                        if hasattr(whisper_response, 'words') and whisper_response.words:
                            words_with_global_timestamps = []
                            for word in whisper_response.words:
                                word_dict = {
                                    "word": word.word,
                                    "start": word.start + chunk_start_offset,  # Add chunk offset
                                    "end": word.end + chunk_start_offset
                                }
                                words_with_global_timestamps.append(word_dict)
                            
                            # Save detailed transcript for this chunk
                            detailed_data = {
                                "text": chunk_transcript,
                                "words": words_with_global_timestamps,
                                "chunk_number": chunk_number,
                                "chunk_start_offset": chunk_start_offset
                            }
                            
                            with open(detailed_transcript_path, "w", encoding="utf-8") as f:
                                json.dump(detailed_data, f, indent=2)
                        
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            error_msg = f"Transcription failed for chunk {i+1}: {str(e)}"
                            with open(db_path, "r+") as dbf:
                                db = json.load(dbf)
                                for job in db["processing_jobs"]:
                                    if job["filename"] == filename:
                                        job["status"] = "error"
                                        job["progress"] = 0
                                        job["error"] = error_msg
                                dbf.seek(0)
                                json.dump(db, dbf, indent=2)
                                dbf.truncate()
                            await notify_progress(filename, 0)
                            # Clean up chunk files
                            for chunk_file in chunk_paths:
                                try:
                                    os.remove(chunk_file)
                                except:
                                    pass
                            return
                        await asyncio.sleep(2)
                
                if chunk_transcript:
                    transcript_chunks.append(chunk_transcript)
                
                # Clean up processed chunk
                try:
                    os.remove(chunk_path)
                except:
                    pass
            
            # Combine all transcripts
            transcript = " ".join(transcript_chunks)
            
            # Combine all detailed timestamp data
            combined_words = []
            for i in range(len(chunk_paths)):
                detailed_transcript_path = f"{os.path.splitext(transcript_path)[0]}_chunk_{i:03d}_detailed.json"
                if os.path.exists(detailed_transcript_path):
                    try:
                        with open(detailed_transcript_path, "r", encoding="utf-8") as f:
                            detailed_data = json.load(f)
                            if "words" in detailed_data:
                                combined_words.extend(detailed_data["words"])
                    except Exception as e:
                        print(f"Error reading detailed transcript {detailed_transcript_path}: {e}")
            
            # Save combined detailed transcript
            if combined_words:
                combined_detailed_path = f"{os.path.splitext(transcript_path)[0]}_detailed.json"
                combined_detailed_data = {
                    "text": transcript,
                    "words": combined_words,
                    "total_chunks": len(chunk_paths)
                }
                with open(combined_detailed_path, "w", encoding="utf-8") as f:
                    json.dump(combined_detailed_data, f, indent=2)
                print(f"Combined detailed transcript saved with {len(combined_words)} words")
            
        else:
            # Process single file (original logic)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await notify_progress(filename, 40, step="transcribing_audio")
                    with open(audio_path, "rb") as audio_file:
                        whisper_response = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json",
                            timestamp_granularities=["word"]
                        )
                    transcript = whisper_response.text
                    
                    # Store detailed transcript with timestamps
                    detailed_transcript_path = f"{os.path.splitext(transcript_path)[0]}_detailed.json"
                    if hasattr(whisper_response, 'words') and whisper_response.words:
                        words_with_timestamps = []
                        for word in whisper_response.words:
                            word_dict = {
                                "word": word.word,
                                "start": word.start,
                                "end": word.end
                            }
                            words_with_timestamps.append(word_dict)
                        
                        # Save detailed transcript
                        detailed_data = {
                            "text": transcript,
                            "words": words_with_timestamps
                        }
                        
                        with open(detailed_transcript_path, "w", encoding="utf-8") as f:
                            json.dump(detailed_data, f, indent=2)
                    
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        error_msg = f"Transcription failed after {max_retries} attempts: {str(e)}"
                        with open(db_path, "r+") as dbf:
                            db = json.load(dbf)
                            for job in db["processing_jobs"]:
                                if job["filename"] == filename:
                                    job["status"] = "error"
                                    job["progress"] = 0
                                    job["error"] = error_msg
                            dbf.seek(0)
                            json.dump(db, dbf, indent=2)
                            dbf.truncate()
                        await notify_progress(filename, 0)
                        return
                    await asyncio.sleep(2)
        
        # Save transcript
        with open(transcript_path, "w", encoding="utf-8") as tf:
            tf.write(transcript)
        await notify_progress(filename, 60, step="transcription_done")
        
        # Chunking and embedding
        await notify_progress(filename, 70, step="chunking_and_embedding")
        from vector_pipeline import process_transcript
        process_transcript(filename)
        await notify_progress(filename, 100, step="done")
        
        # Success
        with open(db_path, "r+") as dbf:
            db = json.load(dbf)
            for job in db["processing_jobs"]:
                if job["filename"] == filename:
                    job["status"] = "done"
                    job["progress"] = 100
                    job["audio_path"] = audio_path
                    job["transcript_path"] = transcript_path
                    job["transcript_metadata"] = {
                        "length": len(transcript) if transcript else 0
                    }
            dbf.seek(0)
            json.dump(db, dbf, indent=2)
            dbf.truncate()
        await notify_progress(filename, 100)
        
    except Exception as e:
        with open(db_path, "r+") as dbf:
            db = json.load(dbf)
            for job in db["processing_jobs"]:
                if job["filename"] == filename:
                    job["status"] = "error"
                    job["progress"] = 0
                    job["error"] = str(e)
            dbf.seek(0)
            json.dump(db, dbf, indent=2)
            dbf.truncate()
        await notify_progress(filename, 0)


@app.get("/")
def root():
    return {"message": "Lecture Chat Backend Running"}



@app.post("/upload")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, restart: bool = False):
    os.makedirs("uploads", exist_ok=True)
    from datetime import datetime
    # Add timestamp to filename
    base, ext = os.path.splitext(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    new_filename = f"{base}_{timestamp}{ext}"
    file_location = f"uploads/{new_filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    # Clean up previous sessions and create a new session
    cleanup_sessions()
    session = create_session(new_filename)
    # If restart requested, remove any previous failed jobs for this file
    if restart:
        db_path = "db.json"
        with open(db_path, "r+") as dbf:
            db = json.load(dbf)
            db["processing_jobs"] = [j for j in db["processing_jobs"] if j["filename"] != new_filename]
            dbf.seek(0)
            json.dump(db, dbf, indent=2)
            dbf.truncate()
    # Enqueue processing job
    if background_tasks is not None:
        background_tasks.add_task(process_job, new_filename)
    return {"filename": new_filename, "status": "uploaded", "session": session}

@app.get("/sessions")
def get_sessions_endpoint():
    """Get all sessions"""
    return {"sessions": get_sessions()}

@app.get("/processing-status")
def get_processing_status():
    """Get status of all processing jobs"""
    db_path = "db.json"
    with open(db_path, "r") as dbf:
        db = json.load(dbf)
        return {"jobs": db.get("processing_jobs", [])}

@app.get("/lectures")
def get_lectures():
    """Get all available lectures for RAG queries"""
    db_path = "db.json"
    with open(db_path, "r") as dbf:
        db = json.load(dbf)
        # Return completed processing jobs as available lectures
        completed_jobs = [job for job in db.get("processing_jobs", []) if job.get("status") == "done"]
        return {"lectures": completed_jobs}

@app.post("/rag-query")
def rag_query_endpoint(query: RAGQuery):
    """Perform RAG query on a specific lecture"""
    try:
        from rag_query import rag_query
        result = rag_query(query.video_id, query.query)
        return {
            "video_id": query.video_id,
            "query": query.query,
            "answer": result["answer"],
            "timestamps": result.get("used_timestamps", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@app.delete("/clear-data")
def clear_all_data():
    """Clear all data - sessions, jobs, and uploaded files"""
    db_path = "db.json"
    with open(db_path, "w") as dbf:
        json.dump({
            "lectures": [],
            "processing_jobs": [],
            "sessions": []
        }, dbf, indent=2)
    
    # Clean up uploaded files
    uploads_dir = "uploads"
    if os.path.exists(uploads_dir):
        for file in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, file)
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    return {"message": "All data cleared successfully"}
