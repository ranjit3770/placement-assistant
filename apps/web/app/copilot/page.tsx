"use client";

import React, { useState } from 'react';
import { useCopilot } from '../../hooks/useCopilot';
import { ChatWindow } from '../../components/copilot/ChatWindow';
import { MessageInput } from '../../components/copilot/MessageInput';
import Link from 'next/link';
import { ChevronLeft, LogIn, Menu } from 'lucide-react';

export default function CopilotPage() {
  const { messages, isLoading, sendMessage, sessionId } = useCopilot();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Quick auth hack for demo purposes
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (tokenInput.trim()) {
      localStorage.setItem('token', tokenInput.trim());
      setIsAuthenticated(true);
      window.location.reload(); // Reload to let hook pick up the new token
    }
  };

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      if (token) {
        setIsAuthenticated(true);
      }
    }
  }, []);

  if (!isAuthenticated) {
    if (process.env.NODE_ENV === 'production') {
      return (
        <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-red-200 w-full max-w-md">
            <h1 className="text-2xl font-semibold text-red-600 mb-2">Unauthorized</h1>
            <p className="text-zinc-500">Authentication is required. Mock login is disabled in production.</p>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">

        <div className="bg-white p-8 rounded-2xl shadow-sm border border-zinc-200 w-full max-w-md">
          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-6">
            <LogIn className="w-6 h-6 text-blue-600" />
          </div>
          <h1 className="text-2xl font-semibold text-zinc-900 mb-2">Sign in to Copilot</h1>
          <p className="text-zinc-500 mb-6">Enter your student JWT to access the Copilot.</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="token" className="block text-sm font-medium text-zinc-700 mb-1">
                Access Token
              </label>
              <input
                id="token"
                type="text"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="eyJhbGciOi..."
                className="w-full px-4 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-blue-600 text-white font-medium py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Sign In
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-zinc-50 overflow-hidden font-sans">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/20 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`fixed inset-y-0 left-0 w-64 bg-white border-r border-zinc-200 z-30 transform transition-transform duration-200 ease-in-out md:translate-x-0 md:static md:flex md:flex-col ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
          <Link href="/" className="text-sm font-medium text-zinc-600 hover:text-zinc-900 flex items-center gap-2 transition-colors">
            <ChevronLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <button 
            className="md:hidden text-zinc-500 hover:text-zinc-900"
            onClick={() => setSidebarOpen(false)}
          >
            ×
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
            Recent Conversations
          </h3>
          <div className="space-y-1">
            <div className={`px-3 py-2 text-sm rounded-lg cursor-pointer ${
                sessionId ? 'bg-zinc-100 text-zinc-900 font-medium' : 'text-zinc-600 hover:bg-zinc-50'
              }`}>
              Current Session
            </div>
          </div>
        </div>
        
        <div className="p-4 border-t border-zinc-200">
          <button 
            onClick={() => {
              localStorage.removeItem('token');
              window.location.reload();
            }}
            className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-zinc-200 flex items-center px-4 md:hidden">
          <button 
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 text-zinc-500 hover:text-zinc-900"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="ml-2 font-medium text-zinc-900">Placement Copilot</h1>
        </header>

        <ChatWindow messages={messages} isLoading={isLoading} />
        
        <div className="mt-auto">
          <MessageInput onSendMessage={sendMessage} disabled={isLoading} />
        </div>
      </main>
    </div>
  );
}
