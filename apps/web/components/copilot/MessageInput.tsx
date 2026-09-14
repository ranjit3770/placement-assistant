import React, { useState, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled: boolean;
}

export function MessageInput({ onSendMessage, disabled }: MessageInputProps) {
  const [content, setContent] = useState('');

  const handleSend = () => {
    if (content.trim() && !disabled) {
      onSendMessage(content);
      setContent('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-zinc-200 bg-white p-4">
      <div className="max-w-3xl mx-auto relative flex items-end shadow-sm border border-zinc-300 rounded-xl bg-white overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-shadow">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your placement eligibility..."
          disabled={disabled}
          rows={1}
          className="w-full resize-none bg-transparent p-4 pr-12 focus:outline-none max-h-32 text-zinc-900 disabled:opacity-50"
          style={{ minHeight: '56px' }}
        />
        <button
          onClick={handleSend}
          disabled={!content.trim() || disabled}
          className="absolute right-2 bottom-2 p-2 rounded-lg text-blue-600 hover:bg-blue-50 disabled:text-zinc-400 disabled:hover:bg-transparent transition-colors"
          aria-label="Send message"
        >
          {disabled ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
      <div className="text-center mt-2">
        <span className="text-xs text-zinc-500">
          AI explanations are not authoritative. Results are based on approved policies.
        </span>
      </div>
    </div>
  );
}
