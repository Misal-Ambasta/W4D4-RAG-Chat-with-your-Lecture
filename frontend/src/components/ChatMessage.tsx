import React from "react";
import TimestampText from "./TimestampText";

export interface ChatMessageProps {
  message: string;
  sender: "user" | "assistant";
  timestamp?: string;
  onTimestampClick?: (timestamp: string) => void;
}

// Helper to find timestamps in text (e.g. 00:12:34)
const TIMESTAMP_REGEX = /\b\d{2}:\d{2}:\d{2}\b/g;

const ChatMessage: React.FC<ChatMessageProps> = ({ message, sender, timestamp, onTimestampClick }) => {
  // Render message with clickable timestamps
  const renderMessage = (text: string) => {
    const parts = text.split(TIMESTAMP_REGEX);
    const matches = text.match(TIMESTAMP_REGEX);
    if (!matches) return text;
    const result: React.ReactNode[] = [];
    parts.forEach((part, idx) => {
      result.push(part);
      if (matches[idx]) {
        result.push(
          <TimestampText
            key={idx}
            timestamp={matches[idx]}
            onClick={onTimestampClick}
          />
        );
      }
    });
    return result;
  };
  return (
    <div className={`flex mb-2 ${sender === "user" ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[70%] px-4 py-2 rounded-lg shadow text-sm whitespace-pre-line ${
        sender === "user"
          ? "bg-blue-500 text-white rounded-br-none"
          : "bg-gray-100 text-gray-800 rounded-bl-none"
      }`}>
        {renderMessage(message)}
        {timestamp && (
          <span className="block text-xs text-gray-400 mt-1 text-right">
            <TimestampText timestamp={timestamp} onClick={onTimestampClick} />
          </span>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
