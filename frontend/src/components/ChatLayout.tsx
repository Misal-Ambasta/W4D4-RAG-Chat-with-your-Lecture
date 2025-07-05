import React from 'react';

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-4">
      <header className="w-full max-w-2xl text-center my-8">
        <h1 className="text-3xl font-bold text-blue-700 mb-2">Lecture Chat</h1>
        <p className="text-gray-500">Chat with your uploaded lecture videos using AI</p>
      </header>
      <main className="w-full max-w-2xl bg-white shadow-md rounded-lg p-6 flex-1 flex flex-col">
        {children}
      </main>
      <footer className="mt-8 text-gray-400 text-xs">&copy; {new Date().getFullYear()} Lecture Chat MVP</footer>
    </div>
  );
}
