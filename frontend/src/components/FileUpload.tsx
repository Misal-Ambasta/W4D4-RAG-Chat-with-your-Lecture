import React, { useRef, useState } from 'react';

interface FileUploadProps {
  onUpload: (file: File) => void;
  uploading: boolean;
  progress: number;
}

export default function FileUpload({ onUpload, uploading, progress }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (file: File) => {
    const allowedTypes = ['video/mp4', 'video/mkv', 'video/webm'];
    const maxSize = 1024 * 1024 * 1024 * 3; // 3GB
    if (!allowedTypes.includes(file.type)) {
      return 'Only MP4, MKV, WEBM files are allowed.';
    }
    if (file.size > maxSize) {
      return 'File size exceeds 3GB limit.';
    }
    return null;
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validation = validateFile(file);
      if (validation) {
        setError(validation);
      } else {
        setError(null);
        onUpload(file);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const validation = validateFile(file);
      if (validation) {
        setError(validation);
      } else {
        setError(null);
        onUpload(file);
      }
    }
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}`}
      onDragOver={e => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={e => { e.preventDefault(); setDragActive(false); }}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/mkv,video/webm"
        className="hidden"
        onChange={handleChange}
        disabled={uploading}
      />
      <div className="mb-2 text-gray-700">Drag & drop a lecture video, or <span className="text-blue-600 underline">browse</span></div>
      <div className="text-xs text-gray-400 mb-2">Supported: MP4, MKV, WEBM. Max size: 3GB</div>
      {error && <div className="text-red-500 text-sm mb-2">{error}</div>}
      {uploading && (
        <div className="w-full bg-gray-200 rounded-full h-3 mt-4">
          <div className="bg-blue-500 h-3 rounded-full" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}
