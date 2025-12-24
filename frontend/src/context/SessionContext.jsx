import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAuth } from './AuthContext';

const SessionContext = createContext();

// Default greeting shown only for NEW sessions (UI only; not sent as a user message)
const DEFAULT_SYSTEM_MESSAGE = { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" };

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};

export const SessionProvider = ({ children }) => {
  const { user, isAuthenticated } = useAuth();

  // Memoize user id to prevent unnecessary rerenders
  const userId = useMemo(() => user?.id || '', [user?.id]);

  const [messages, setMessages] = useState(() => [{ ...DEFAULT_SYSTEM_MESSAGE }]);
  const [userDisplayName, setUserDisplayName] = useState('');
  const [personality, setPersonality] = useState(null);
  const [conversationTopics, setConversationTopics] = useState([]);
  const [sessionIdState, setSessionIdState] = useState(null);
  const sessionIdRef = useRef(null);
  const setSessionId = useCallback((nextSessionId) => {
    sessionIdRef.current = nextSessionId;
    setSessionIdState(nextSessionId);
  }, []);
  const getSessionId = useCallback(() => sessionIdRef.current, []);

  const previousUserIdRef = useRef(null);

  // Memoize user properties to prevent unnecessary rerenders
  const userDisplayNameFromAuth = useMemo(() =>
    user?.metadata?.display_name || user?.display_name || user?.email || '',
    [user?.metadata?.display_name, user?.display_name, user?.email]
  );
  const userPersonalityFromAuth = useMemo(() => user?.personality, [user?.personality]);
  const prevPersonalityRef = useRef(null);

  useEffect(() => {
    if (!isAuthenticated || !userId) {
      setMessages([{ ...DEFAULT_SYSTEM_MESSAGE }]);
      setUserDisplayName('');
      setPersonality(null);
      setConversationTopics([]);
      setSessionId(null);
      previousUserIdRef.current = null;
      prevPersonalityRef.current = null;
      return;
    }

    // Update display name if changed
    if (userDisplayNameFromAuth && userDisplayNameFromAuth !== userDisplayName) {
      setUserDisplayName(userDisplayNameFromAuth);
    }

    // Update personality if changed
    const currentPersonalityStr = JSON.stringify(userPersonalityFromAuth);
    const prevPersonalityStr = JSON.stringify(prevPersonalityRef.current);
    if (userPersonalityFromAuth && currentPersonalityStr !== prevPersonalityStr) {
      setPersonality(userPersonalityFromAuth);
      prevPersonalityRef.current = userPersonalityFromAuth;
    }

    // Reset conversation when user changes
    if (previousUserIdRef.current && previousUserIdRef.current !== userId) {
      setMessages([{ ...DEFAULT_SYSTEM_MESSAGE }]);
      setConversationTopics([]);
      setSessionId(null);
      prevPersonalityRef.current = null;
    }

    previousUserIdRef.current = userId;
  }, [isAuthenticated, userId, userDisplayNameFromAuth, userPersonalityFromAuth, userDisplayName, setSessionId]);

  const updateMessages = useCallback((newMessages) => {
    setMessages(newMessages);
  }, []);

  const addMessage = useCallback((message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const updatePersonality = useCallback((newPersonality) => {
    setPersonality(newPersonality);
  }, []);

  const updateUserDisplayName = useCallback((newDisplayName) => {
    setUserDisplayName(newDisplayName);
  }, []);

  const updateConversationTopics = useCallback((topics) => {
    setConversationTopics(topics);
  }, []);

  const resetSession = useCallback(() => {
    setMessages([{ ...DEFAULT_SYSTEM_MESSAGE }]);
    setConversationTopics([]);
    setSessionId(null);
  }, [setSessionId]);

  const switchSession = useCallback((newSessionId, initialMessages = null) => {
    setSessionId(newSessionId);
    // We currently don't load chat history for sessions; start with an empty UI.
    // The system message is still added automatically to API payloads when sending.
    if (initialMessages && Array.isArray(initialMessages)) {
      setMessages(initialMessages);
    } else {
      setMessages([]);
    }
    setConversationTopics([]);
  }, [setSessionId]);

  const startNewSession = useCallback(() => {
    setSessionId(null);
    setMessages([{ ...DEFAULT_SYSTEM_MESSAGE }]);
    setConversationTopics([]);
  }, [setSessionId]);

  const value = useMemo(() => ({
    // State
    userId,
    messages,
    userDisplayName,
    personality,
    conversationTopics,
    sessionId: sessionIdState,

    // Actions
    updateMessages,
    addMessage,
    updatePersonality,
    updateUserDisplayName,
    updateConversationTopics,
    resetSession,
    switchSession,
    startNewSession,
    setSessionId,
    getSessionId,
  }), [userId, messages, userDisplayName, personality, conversationTopics, sessionIdState, updateMessages, addMessage, updatePersonality, updateUserDisplayName, updateConversationTopics, resetSession, switchSession, startNewSession, setSessionId, getSessionId]);

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
};
