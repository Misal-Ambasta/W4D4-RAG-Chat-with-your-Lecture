import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
import json
import glob
import re

# CONFIGURABLE PARAMETERS
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
CHROMA_PATH = "chroma_db"

def find_timestamp_for_text(text_chunk: str, words_with_timestamps: list) -> dict:
    """
    Find the start and end timestamps for a given text chunk
    """
    # Clean the text chunk for matching
    chunk_words = text_chunk.strip().split()
    if not chunk_words:
        return {"start": 0, "end": 0}
    
    # Find the first word of the chunk in the timestamp data
    first_word = chunk_words[0].lower().strip('.,!?";')
    last_word = chunk_words[-1].lower().strip('.,!?";')
    
    start_time = None
    end_time = None
    
    # Find start time
    for word_data in words_with_timestamps:
        if word_data["word"].lower().strip('.,!?";') == first_word:
            start_time = word_data["start"]
            break
    
    # Find end time (search from the end)
    for word_data in reversed(words_with_timestamps):
        if word_data["word"].lower().strip('.,!?";') == last_word:
            end_time = word_data["end"]
            break
    
    return {
        "start": start_time or 0,
        "end": end_time or 0
    }

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def process_transcript(filename: str):
    import os
    import json
    import glob
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
    from langchain.docstore.document import Document

    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    CHROMA_PATH = "chroma_db"

    db_path = "db.json"
    transcript_path = os.path.join("uploads", f"{os.path.splitext(filename)[0]}.transcript.txt")
    base_name = os.path.splitext(transcript_path)[0]
    video_id = filename

    import re
    def sanitize_collection_name(name: str) -> str:
        # Remove invalid characters, replace spaces and periods, ensure valid start/end
        name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        name = re.sub(r'^[^a-zA-Z0-9]+', '', name)  # Remove invalid start
        name = re.sub(r'[^a-zA-Z0-9]+$', '', name)  # Remove invalid end
        name = re.sub(r'\.[^.]+$', '', name)  # Remove file extension
        return name
    sanitized_collection = f"lecture_{sanitize_collection_name(video_id)}"

    if not os.path.exists(transcript_path):
        print(f"Transcript not found for {filename}")
        return

    # Read the main transcript
    with open(transcript_path, "r", encoding="utf-8") as tf:
        transcript = tf.read()

    # Collect all timestamp data from detailed transcripts
    all_words_with_timestamps = []
    
    # Check for detailed transcript files (both single file and chunked)
    detailed_files = glob.glob(f"{base_name}_detailed.json") + glob.glob(f"{base_name}_chunk_*_detailed.json")
    
    if detailed_files:
        for detailed_file in sorted(detailed_files):
            try:
                with open(detailed_file, "r", encoding="utf-8") as f:
                    detailed_data = json.load(f)
                    if "words" in detailed_data:
                        all_words_with_timestamps.extend(detailed_data["words"])
            except Exception as e:
                print(f"Error reading {detailed_file}: {e}")
    
    print(f"Found {len(all_words_with_timestamps)} words with timestamps")

    # Chunk transcript
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.create_documents([transcript])
    
    # Attach metadata including timestamps
    docs = []
    for i, chunk in enumerate(chunks):
        # Find timestamp for this chunk
        timestamp_info = find_timestamp_for_text(chunk.page_content, all_words_with_timestamps)
        
        metadata = {
            "video_id": video_id,
            "chunk_index": i,
            "start_time": timestamp_info["start"],
            "end_time": timestamp_info["end"],
            "timestamp": format_timestamp(timestamp_info["start"]),
            "timestamp_end": format_timestamp(timestamp_info["end"])
        }
        
        docs.append(Document(page_content=chunk.page_content, metadata=metadata))
    
    # Store in ChromaDB
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectordb = Chroma(
        collection_name=sanitized_collection,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH
    )
    vectordb.add_documents(docs)
    print(f"Processed and stored {len(docs)} chunks with timestamps for {video_id}")
    
    # Don't cleanup transcript files during development - keep them for debugging
    print(f"Transcript files preserved for debugging")
    # Cleanup only audio files to save space
    try:
        audio_path = os.path.join("uploads", f"{os.path.splitext(filename)[0]}.mp3")
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"Cleaned up audio file: {audio_path}")
    except Exception as cleanup_err:
        print(f"Cleanup error: {cleanup_err}")
