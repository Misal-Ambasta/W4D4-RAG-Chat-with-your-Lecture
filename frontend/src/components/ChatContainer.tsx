import React, { useState } from "react";
import ChatWindow from "./ChatWindow";
import ChatInput from "./ChatInput";
import ProcessingStatus from "./ProcessingStatus";
import type { ChatMessageProps } from "./ChatMessage";

interface ChatContainerProps {
  onTimestampJump?: (timestamp: string) => void;
  videoFile?: string; // Add videoFile prop
  onUploadNew?: () => void;
}

const ChatContainer: React.FC<ChatContainerProps> = ({ onTimestampJump, videoFile, onUploadNew }) => {
  const [messages, setMessages] = useState<ChatMessageProps[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"queued" | "processing" | "done" | "error">("done");
  const [progress, setProgress] = useState(100);
  const [error, setError] = useState<string | undefined>(undefined);
  const [step, setStep] = useState<string | undefined>(undefined);
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null);

  // Get available lectures on component mount
  React.useEffect(() => {
    const fetchLectures = async () => {
      try {
        const response = await fetch('http://localhost:8000/lectures');
        const data = await response.json();
        if (data.lectures && data.lectures.length > 0) {
          // Use the most recent lecture
          const latestLecture = data.lectures[data.lectures.length - 1];
          setCurrentVideoId(latestLecture.filename);
          
          // Add welcome message
          setMessages([{
            message: `Welcome! I'm ready to answer questions about your lecture: "${latestLecture.filename}". You can ask me anything about the content, key concepts, or specific topics covered in the lecture.`,
            sender: "assistant"
          }]);
        }
      } catch (err) {
        console.error('Failed to fetch lectures:', err);
        setError('Failed to load lecture data');
      }
    };
    fetchLectures();
  }, []);

  // WebSocket connection for backend processing status (removed since you removed it from backend)
  React.useEffect(() => {
    // WebSocket functionality removed as it's not implemented in the backend
  }, [status]);

  // Convert hh:mm:ss to seconds
  const parseTimestamp = (ts: string): number => {
    const parts = ts.split(":").map(Number);
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }
    return 0;
  };

  // Format to mm:ss
  const formatTimestamp = (ts: string): string => {
    const totalSeconds = parseTimestamp(ts);
    const mm = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
    const ss = (totalSeconds % 60).toString().padStart(2, "0");
    return `${mm}:${ss}`;
  };

  // Make actual RAG query to backend
  const handleSend = async (message: string) => {
    if (!currentVideoId) {
      setMessages(prev => [...prev, 
        { message, sender: "user" },
        { message: "No lecture is currently loaded. Please upload a lecture first.", sender: "assistant" }
      ]);
      return;
    }

    setMessages(prev => [...prev, { message, sender: "user" }]);
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/rag-query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: currentVideoId,
          query: message
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Extract timestamps from the answer if they exist
      // Capture either mm:ss or hh:mm:ss timestamps
      const timestampRegex = /\b(\d{1,2}:\d{2}(?::\d{2})?)\b/g;
      const timestamps = [...data.answer.matchAll(timestampRegex)].map(match => match[1]);
      
      setMessages(prev => [
        ...prev,
        {
          message: data.answer,
          sender: "assistant",
          timestamp: timestamps.length > 0 ? formatTimestamp(timestamps[0]) : undefined
        }
      ]);
    } catch (err) {
      console.error('RAG query failed:', err);
      setMessages(prev => [
        ...prev,
        {
          message: "Sorry, I encountered an error while processing your question. Please try again.",
          sender: "assistant"
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handle timestamp click in chat
  const handleTimestampClick = (ts: string) => {
    if (onTimestampJump) {
      onTimestampJump(ts);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-md max-w-2xl mx-auto my-4 p-2 md:p-4 min-h-[70vh]">
      {/* Navigation */}
      <nav className="flex items-center justify-between mb-2">
        <div className="text-xl font-bold text-blue-700">Lecture Chat</div>
        <div className="text-sm text-gray-600">
          {currentVideoId ? `Chatting with: ${currentVideoId}` : 'No lecture loaded'}
        </div>
        <button className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition" onClick={onUploadNew}>Upload New</button>
      </nav>
      {/* Processing Status */}
      <ProcessingStatus status={status} error={error} />
      {/* Chat Window */}
      <div className="flex-1 min-h-[300px] flex flex-col">
        <ChatWindow
          messages={messages.map(msg => ({
            ...msg,
            onTimestampClick: msg.timestamp ? handleTimestampClick : undefined,
          }))}
          loading={loading}
        />
      </div>
      {loading && (
        <div className="flex items-center gap-2 justify-center p-2 text-blue-600">
          <svg className="animate-spin h-4 w-4 text-blue-500 mr-1" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="font-semibold">Thinking...</span>
        </div>
      )}
      <ChatInput onSend={handleSend} loading={loading} />
    </div>
  );
};

export default ChatContainer;
