import React from "react";

export interface ProcessingStatusProps {
  status: "queued" | "processing" | "done" | "error";
  error?: string;
}


const spinner = (
  <svg className="animate-spin h-4 w-4 text-blue-500 mr-1" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
  </svg>
);

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ status, error }) => {
  if (status === "processing" || status === "queued") {
    return (
      <div className="flex items-center gap-2 text-sm min-h-[32px]">
        {spinner}
        <span className="text-blue-600 font-semibold">Processing, please wait...</span>
      </div>
    );
  }
  if (status === "done") {
    return (
      <div className="flex items-center gap-2 text-sm min-h-[32px]">
        <span className="text-green-600 font-semibold">All processing done successfully.</span>
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="flex items-center gap-2 text-sm min-h-[32px]">
        <span className="text-red-500 font-semibold">Error: {error || "Processing failed."}</span>
      </div>
    );
  }
  return null;
};

export default ProcessingStatus;
