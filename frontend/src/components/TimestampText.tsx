import React from "react";

export interface TimestampTextProps {
  timestamp: string;
  onClick?: (timestamp: string) => void;
}

const TimestampText: React.FC<TimestampTextProps> = ({ timestamp, onClick }) => {
  return (
    <span
      className="text-blue-600 underline cursor-pointer hover:text-blue-800 transition"
      onClick={() => onClick && onClick(timestamp)}
    >
      {timestamp}
    </span>
  );
};

export default TimestampText;
