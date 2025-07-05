import React, { useState } from "react";

export interface ChatInputProps {
  onSend: (message: string) => void;
  loading?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, loading }) => {
  const [input, setInput] = useState("");

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSend(input.trim());
      setInput("");
    }
  };

  return (
    <form onSubmit={handleSend} className="flex items-center gap-2 p-2 border-t bg-white">
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        className="flex-1 px-4 py-2 rounded border focus:outline-none focus:ring"
        placeholder="Type your question..."
        disabled={loading}
      />
      <button
        type="submit"
        className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
        disabled={loading || !input.trim()}
      >
        Send
      </button>
    </form>
  );
};

export default ChatInput;
