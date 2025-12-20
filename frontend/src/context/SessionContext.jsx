import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAuth } from './AuthContext';

const SessionContext = createContext();

// Move defaultSystemMessage outside component to prevent recreation
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

  const [messages, setMessages] = useState(() => [
    { ...DEFAULT_SYSTEM_MESSAGE }
  ]);
  const [userDisplayName, setUserDisplayName] = useState('');
  const [personality, setPersonality] = useState(null);
  const [conversationTopics, setConversationTopics] = useState([]);
  const [sessionId, setSessionId] = useState(null);

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
      prevPersonalityRef.current = null;
    }

    previousUserIdRef.current = userId;
  }, [isAuthenticated, userId, userDisplayNameFromAuth, userPersonalityFromAuth, userDisplayName]);

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
  }, []);

  const switchSession = useCallback((newSessionId, initialMessages = null) => {
    setSessionId(newSessionId);
    // If initial messages provided, use them; otherwise start with system message
    if (initialMessages && Array.isArray(initialMessages) && initialMessages.length > 0) {
        //TODO if we need to enable initial message when switching sessions
      // setMessages(initialMessages);
    } else {
      // setMessages([{ ...DEFAULT_SYSTEM_MESSAGE }]);
    }
    setConversationTopics([]);
  }, []);

  const startNewSession = useCallback(() => {
    setSessionId(null);
    setMessages([{ ...DEFAULT_SYSTEM_MESSAGE }]);
    setConversationTopics([]);
  }, []);

  const value = useMemo(() => ({
    // State
    userId,
    messages,
    userDisplayName,
    personality,
    conversationTopics,
    sessionId,

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
  }), [userId, messages, userDisplayName, personality, conversationTopics, sessionId, updateMessages, addMessage, updatePersonality, updateUserDisplayName, updateConversationTopics, resetSession, switchSession, startNewSession]);

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
};
