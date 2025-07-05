import os
import json
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CHROMA_PATH = "chroma_db"

def rag_query(video_id, user_query):
    """
    Perform RAG query on a specific lecture video
    
    Args:
        video_id: The filename of the video to query
        user_query: The user's question
        
    Returns:
        dict: Contains answer and used_timestamps
    """
    try:
        # --- Query preprocessing (simple: strip/clean) ---
        query = user_query.strip()
        
        if not query:
            return {"answer": "Please provide a valid question.", "used_timestamps": []}

        # --- Semantic search in ChromaDB ---
        import re
        def sanitize_collection_name(name: str) -> str:
            name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
            name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
            name = re.sub(r'[^a-zA-Z0-9]+$', '', name)
            name = re.sub(r'\.[^.]+$', '', name)
            return name
        sanitized_collection = f"lecture_{sanitize_collection_name(video_id)}"
        
        try:
            vectordb = Chroma(
                collection_name=sanitized_collection,
                embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
                persist_directory=CHROMA_PATH
            )
        except Exception as e:
            return {"answer": f"Error accessing vector database for {video_id}. Please ensure the lecture has been processed. Error: {str(e)}", "used_timestamps": []}
        
        # Efficient chunk retrieval with score filtering and cache
        cache = getattr(rag_query, "_cache", None)
        if cache is None:
            cache = {}
            setattr(rag_query, "_cache", cache)
        cache_key = f"{video_id}:{query}"
        if cache_key in cache:
            docs_scores = cache[cache_key]
        else:
            try:
                docs_scores = vectordb.similarity_search_with_score(query, k=8)
                cache[cache_key] = docs_scores
            except Exception as e:
                return {"answer": f"Error searching for relevant content: {str(e)}", "used_timestamps": []}
        
        # Filter by score threshold (lower is more similar)
        threshold = 2.0  # Increased threshold to allow more results
        docs = [doc for doc, score in docs_scores if score <= threshold][:4]
        
        if not docs:
            return {"answer": "I couldn't find relevant information in the lecture to answer your question. Please try rephrasing your question.", "used_timestamps": []}
        
        # --- Context retrieval with relevance scoring ---
        context = "\n---\n".join([d.page_content for d in docs])
        # Extract timestamps from metadata
        timestamps = []
        for d in docs:
            if d.metadata.get("timestamp"):
                timestamps.append(d.metadata["timestamp"])
            elif d.metadata.get("start_time") is not None:
                # Format timestamp from seconds
                start_seconds = d.metadata["start_time"]
                minutes = int(start_seconds // 60)
                seconds = int(start_seconds % 60)
                timestamp_str = f"{minutes:02d}:{seconds:02d}"
                timestamps.append(timestamp_str)
        
        # Remove duplicates while preserving order
        unique_timestamps = list(dict.fromkeys(timestamps))
        
        # --- Response generation with OpenAI GPT-4o mini ---
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful lecture assistant. Use the provided context to answer the user's question. Always include relevant timestamps from the context if available. If you cannot answer the question based on the context, say so clearly. When timestamps are available, format them as [MM:SS] in your response."),
            ("human", "Context:\n{context}\n\nAvailable timestamps: {timestamps}\n\nQuestion: {question}\nAnswer (include timestamps when relevant):")
        ])
        
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
            chain = prompt | llm
            response = chain.invoke({
                "context": context, 
                "question": query,
                "timestamps": ", ".join(unique_timestamps) if unique_timestamps else "No timestamps available"
            })
            
            return {
                "answer": response.content,
                "used_timestamps": unique_timestamps
            }
        except Exception as e:
            return {"answer": f"Error generating response: {str(e)}", "used_timestamps": []}
            
    except Exception as e:
        return {"answer": f"Unexpected error: {str(e)}", "used_timestamps": []}

if __name__ == "__main__":
    # Load job info safely
    try:
        with open("db.json", "r") as dbf:
            db = json.load(dbf)
            jobs = db.get("processing_jobs", [])
    except FileNotFoundError:
        print("db.json not found. No jobs to process.")
        jobs = []
    except json.JSONDecodeError:
        print("Invalid JSON in db.json. No jobs to process.")
        jobs = []
    
    # Example usage for completed jobs
    completed_jobs = [job for job in jobs if job.get("status") == "done"]
    
    if not completed_jobs:
        print("No completed jobs found for testing.")
    else:
        for job in completed_jobs:
            video_id = job.get("filename")
            if not video_id:
                continue
            user_query = "Summarize the main topic of this lecture."
            result = rag_query(video_id, user_query)
            print(f"Lecture: {video_id}\nAnswer: {result['answer']}\nTimestamps: {result['used_timestamps']}\n---\n")
