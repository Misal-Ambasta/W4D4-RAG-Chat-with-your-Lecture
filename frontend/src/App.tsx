import ChatLayout from './components/ChatLayout';
import FileUpload from './components/FileUpload';
import ChatContainer from './components/ChatContainer';
import ProcessingStatus from './components/ProcessingStatus';
import { useEffect, useRef, useState } from 'react';

function App() {
  // Placeholder for WebSocket connection
  const ws = useRef<WebSocket | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string; filename?: string; status?: string; session?: any } | null>(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws');
    ws.current.onopen = () => console.log('WebSocket connected');
    ws.current.onclose = () => console.log('WebSocket closed');
    ws.current.onerror = (e) => console.error('WebSocket error', e);
    return () => { ws.current?.close(); };
  }, []);

  const handleUpload = async (file: File) => {
    setProcessing(true);
    setShowChat(false);
    setUploading(true);
    setProgress(0);
    setUploadStatus(null);
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://localhost:8000/upload', true);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      setUploading(false);
      if (xhr.status === 200) {
        try {
          const response = JSON.parse(xhr.responseText);
          setUploadStatus({
            success: true,
            message: 'Upload successful!',
            filename: response.filename,
            status: response.status,
            session: response.session
          });
        } catch (e) {
          setUploadStatus({ success: true, message: 'Upload successful!' });
        }
      } else {
        setUploadStatus({ success: false, message: 'Upload failed.' });
      }
    };
    xhr.onerror = () => {
      setUploading(false);
      setUploadStatus({ success: false, message: 'Upload failed.' });
    };

    xhr.send(formData);
  };

  // State for controlling chat interface visibility
  const [showChat, setShowChat] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<{ status: string; error?: string }>({ status: "queued" });
  const [videoFile, setVideoFile] = useState<string | null>(null);

  // Listen for uploadStatus and switch to chat interface after upload and processing
  useEffect(() => {
    if (uploadStatus?.success) {
      setProcessing(true);
      setShowChat(false);
      // Poll the backend for processing status
      const poll = async () => {
        try {
          const res = await fetch('http://localhost:8000/processing-status');
          const data = await res.json();
          // Find the latest job for this file
          const job = data.jobs && data.jobs.length > 0 ? data.jobs[data.jobs.length - 1] : null;
          if (job) {
            setProcessingStatus({
              status: job.status,
              error: job.error
            });
            if (job.status === "done") {
              setProcessing(false);
              setShowChat(true);
              return;
            }
            if (job.status === "error") {
              setProcessing(false);
              setShowChat(false);
              return;
            }
          }
        } catch (err) {
          setProcessingStatus({ status: "error", error: "Failed to fetch processing status." });
          setProcessing(false);
          setShowChat(false);
          return;
        }
        setTimeout(poll, 2000);
      };
      poll();
      setVideoFile((prev) => prev || (typeof uploadStatus === 'object' ? uploadStatus.filename : null));
    }
  }, [uploadStatus]);

  return (
    <ChatLayout>
      {!showChat && (
        <div className="flex flex-col gap-4 items-center justify-center">
          <h2 className="text-xl font-semibold text-gray-700">Welcome to Lecture Chat</h2>
          <div className="text-gray-500">Upload a lecture video and start chatting with its content!</div>
          <FileUpload onUpload={handleUpload} uploading={uploading} progress={progress} />
          {uploadStatus && <div className={uploadStatus.success ? 'text-green-600' : 'text-red-600'}>{uploadStatus.message}</div>}
          {processing && (
            <div className="w-full max-w-md mt-6">
              <ProcessingStatus status={processingStatus.status as any} error={processingStatus.error} />
            </div>
          )}
        </div>
      )}
      {showChat && (
        <div className="w-full">
          <ChatContainer videoFile={videoFile || undefined} onUploadNew={() => {
            setShowChat(false);
            setVideoFile(null);
            setUploadStatus(null);
            setProcessing(false);
            setProcessingStatus({ status: "queued" });
          }} />
        </div>
      )}
    </ChatLayout>
  );
}

export default App
