import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from '../context/SessionContext';
import { getAllChatSessions, getChatHistory } from '../services/api';
import '../styles/SessionHistory.css';

const SessionHistory = () => {
  const { sessionId, switchSession, startNewSession } = useSession();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingHistoryForSession, setLoadingHistoryForSession] = useState(null);

  // Fetch all sessions on component mount
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getAllChatSessions();
        setSessions(data || []);
      } catch (err) {
        console.error('Error fetching sessions:', err);
        setError('Failed to load sessions');
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []); // Only fetch on mount

  // Transform chat history API response to message format
  const transformChatHistoryToMessages = (history) => {
    if (!Array.isArray(history) || history.length === 0) {
      return [];
    }

    const messages = [];
    history.forEach((item) => {
      // Add user message (question)
      if (item.question) {
        messages.push({
          role: 'user',
          content: item.question,
          created_at: item.created_at
        });
      }
      // Add assistant message (answer)
      if (item.answer) {
        messages.push({
          role: 'assistant',
          content: item.answer,
          created_at: item.created_at
        });
      }
    });

    return messages;
  };

  // Handle clicking on a session
  const handleSessionClick = async (clickedSessionId, session) => {
    try {
      // Convert to string for comparison
      const clickedSessionIdStr = String(clickedSessionId);
      const currentSessionIdStr = sessionId ? String(sessionId) : null;

      // If clicking on the same session, do nothing
      if (clickedSessionIdStr === currentSessionIdStr) {
        return;
      }

      // Fetch chat history for the selected session
      setLoadingHistory(true);
      setLoadingHistoryForSession(clickedSessionIdStr);
      try {
        const history = await getChatHistory(clickedSessionIdStr, 1000);
        const transformedMessages = transformChatHistoryToMessages(history);

        // Switch to the selected session with loaded history
        switchSession(clickedSessionIdStr, transformedMessages);
      } catch (historyError) {
        console.error('Error loading chat history:', historyError);
        // Still switch to the session even if history fails to load
        switchSession(clickedSessionIdStr, []);
      } finally {
        setLoadingHistory(false);
        setLoadingHistoryForSession(null);
      }
    } catch (err) {
      console.error('Error switching session:', err);
      setError('Failed to switch session');
      setLoadingHistory(false);
    }
  };

  // Handle creating a new session
  const handleNewSession = async () => {
    try {
      // Reset locally - the session will be created when user sends their first message
      startNewSession();
    } catch (err) {
      console.error('Error creating new session:', err);
      setError('Failed to create new session');
    }
  };

  // Function to refresh sessions list (can be called from outside)
  const refreshSessions = useCallback(async () => {
    try {
      const updatedSessions = await getAllChatSessions();
      setSessions(updatedSessions || []);
    } catch (err) {
      console.error('Error refreshing sessions:', err);
    }
  }, []);

  // Expose refresh function via window for ChatPage to call
  useEffect(() => {
    window.refreshSessionsList = refreshSessions;
    return () => {
      delete window.refreshSessionsList;
    };
  }, [refreshSessions]);

  return (
    <div className="session-history">
      <h3>Sessions</h3>
      {loading ? (
        <div className="session-loading">Loading sessions...</div>
      ) : error ? (
        <div className="session-error">{error}</div>
      ) : (
        <ul>
          {sessions.length === 0 ? (
            <li className="no-sessions">No sessions yet</li>
          ) : (
            sessions.map((session) => {
              // Convert both IDs to strings for comparison
              const sessionIdStr = String(session.id);
              const currentSessionIdStr = sessionId ? String(sessionId) : null;
              const isActive = sessionIdStr === currentSessionIdStr;

              return (
                <li
                  key={session.id}
                  className={isActive ? 'active' : ''}
                >
                  <button
                    type="button"
                    onClick={() => handleSessionClick(session.id, session)}
                    title={session.name || session.id}
                    disabled={loadingHistory && loadingHistoryForSession === sessionIdStr}
                  >
                    {loadingHistory && loadingHistoryForSession === sessionIdStr ? (
                      <>Loading history...</>
                    ) : (
                      session.name || 'Untitled Session'
                    )}
                  </button>
                </li>
              );
            })
          )}
        </ul>
      )}
      <button type="button" className="new-session" onClick={handleNewSession}>
        + New Session
      </button>
    </div>
  );
};

export default SessionHistory;
