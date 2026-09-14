import { useState, useCallback, useEffect } from 'react';

export type Role = 'user' | 'assistant';

export interface Message {
  id: string;
  role: Role;
  content: string;
  decision?: any;
  evidence?: any[];
  isStreaming?: boolean;
}

export function useCopilot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // Note: in a real implementation we would fetch the token from auth context or cookies
  const getAuthHeader = () => {
    // Hardcoded for M9 UI demo purposes until real auth is hooked up
    // In actual app, get from Context/Cookie
    return typeof document !== 'undefined' ? 
      localStorage.getItem('token') || '' : '';
  };

  const getBaseUrl = () => {
    // Assuming API runs on port 8000
    return 'http://localhost:8000/api/v1/copilot';
  };

  const createSession = useCallback(async () => {
    try {
      const res = await fetch(`${getBaseUrl()}/conversations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthHeader()}`,
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.id);
        return data.id;
      }
    } catch (e) {
      console.error("Failed to create session", e);
    }
    return null;
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${getBaseUrl()}/conversations`, {
        headers: {
          'Authorization': `Bearer ${getAuthHeader()}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.length > 0) {
          setSessionId(data[0].id);
          // fetch history
          loadHistory(data[0].id);
        } else {
          createSession();
        }
      } else if (res.status === 401) {
        // Need login
      }
    } catch (e) {
      console.error(e);
    }
  }, [createSession]);

  const loadHistory = async (id: string) => {
    try {
      const res = await fetch(`${getBaseUrl()}/conversations/${id}`, {
        headers: {
          'Authorization': `Bearer ${getAuthHeader()}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content || '',
          decision: m.decision,
          evidence: m.evidence
        })));
      }
    } catch(e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (getAuthHeader()) {
      loadSessions();
    }
  }, [loadSessions]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      currentSessionId = await createSession();
      if (!currentSessionId) return;
    }

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content
    };

    setMessages(prev => [...prev, newMessage]);
    setIsLoading(true);

    try {
      const res = await fetch(`${getBaseUrl()}/conversations/${currentSessionId}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthHeader()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
          id: data.id || Date.now().toString(),
          role: 'assistant',
          content: data.message || 'An error occurred.',
          decision: data.decision,
          evidence: data.evidence,
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error communicating with the server.'
        }]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, a network error occurred.'
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, createSession]);

  return {
    messages,
    isLoading,
    sendMessage,
    sessionId
  };
}
