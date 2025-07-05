import React, { useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import type { ChatMessageProps } from "./ChatMessage";

interface ChatWindowProps {
  messages: ChatMessageProps[];
  loading?: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ messages, loading }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-2 py-4 bg-gray-50">
      {messages.map((msg, idx) => (
        <ChatMessage key={idx} {...msg} />
      ))}
      {loading && (
        <div className="flex justify-start mb-2">
          <div className="max-w-[70%] px-4 py-2 rounded-lg shadow bg-gray-200 text-gray-500 text-sm animate-pulse">
            Generating response...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
};

export default ChatWindow;
