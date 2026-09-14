import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import { Message } from '../../hooks/useCopilot';
import { DecisionCard } from './DecisionCard';
import { EvidenceCard } from './EvidenceCard';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
}

export function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (endOfMessagesRef.current) {
      endOfMessagesRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-50 p-4 sm:p-6 pb-20">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.length === 0 && (
          <div className="text-center py-20">
            <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-blue-600" />
            </div>
            <h2 className="text-2xl font-semibold text-zinc-900 mb-2">Student AI Copilot</h2>
            <p className="text-zinc-500 max-w-md mx-auto">
              I can help you understand your placement eligibility, explain company requirements, and clarify campus policies.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                msg.role === 'user' ? 'bg-zinc-800' : 'bg-blue-600'
              }`}
            >
              {msg.role === 'user' ? (
                <User className="w-5 h-5 text-white" />
              ) : (
                <Bot className="w-5 h-5 text-white" />
              )}
            </div>

            <div
              className={`max-w-[85%] rounded-2xl px-5 py-3.5 ${
                msg.role === 'user'
                  ? 'bg-zinc-800 text-white rounded-tr-none'
                  : 'bg-white border border-zinc-200 text-zinc-900 rounded-tl-none shadow-sm prose prose-blue prose-sm'
              }`}
            >
              {msg.role === 'user' ? (
                <p className="whitespace-pre-wrap m-0">{msg.content}</p>
              ) : (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
                {msg.decision && <DecisionCard decision={msg.decision} />}
                {msg.evidence && <EvidenceCard evidence={msg.evidence} />}
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-white border border-zinc-200 rounded-2xl rounded-tl-none px-5 py-4 shadow-sm flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
            </div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>
    </div>
  );
}
