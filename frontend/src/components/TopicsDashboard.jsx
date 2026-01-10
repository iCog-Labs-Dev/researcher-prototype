import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from '../context/SessionContext';
import { useAuth } from '../context/AuthContext';
import TopicsHeader from './TopicsHeader';
import TopicsFilters from './TopicsFilters';
import MotivationStats from './MotivationStats';
import EngineSettings from './EngineSettings';
import AddTopicForm from './AddTopicForm';
import ErrorModal from './ErrorModal';
import {
    getAllTopicSuggestions,
    getTopicStatistics,
    deleteSessionTopics,
    deleteTopicById,
    cleanupTopics,
    deleteNonActivatedTopics,
    enableTopicResearchById,
    disableTopicResearchById,
} from '../services/api';
import {
  startResearchEngine,
  stopResearchEngine,
  triggerManualResearch,
  getResearchEngineStatus
} from '../services/adminApi';
import '../styles/TopicsDashboard.css';

const TopicsDashboard = () => {
  const { userId } = useSession();
  const { user: authUser } = useAuth();
  const isAdmin = (authUser?.role ?? authUser?.metadata?.role) === 'admin';
  const [topics, setTopics] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState(new Set());
  const [researchEngineStatus, setResearchEngineStatus] = useState(null);
  const [researchEngineLoading, setResearchEngineLoading] = useState(false);
  const [immediateResearchLoading, setImmediateResearchLoading] = useState(false);
  const [activeTopicsCount, setActiveTopicsCount] = useState(0);
  const [showMotivation, setShowMotivation] = useState(false);
  const [showEngineSettings, setShowEngineSettings] = useState(false);
  const [showAddTopicForm, setShowAddTopicForm] = useState(false);
  const [filters, setFilters] = useState({
    searchTerm: '',
    sessionFilter: 'all',
    confidenceFilter: 'all',
    researchStatus: 'all',
    sortBy: 'date',
    sortOrder: 'desc', // asc, desc
    autoOnly: false,
    groupBy: 'parent', // none | parent
  });
  const [expandedTopics, setExpandedTopics] = useState(new Set());
  const [expandedParents, setExpandedParents] = useState(new Set());

  // Helper function to format dates
const formatDate = (dateString) => {
  if (!dateString) return 'N/A';

  const date = new Date(dateString);

  if (isNaN(date.getTime())) return 'N/A';

  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
};

  // Load topics and stats
  const loadData = useCallback(async (preserveError = false) => {
    try {
      setLoading(true);
      if (!preserveError) {
        setError(null);
      }

      const [topicsResponse, statsResponse, engineStatus] = await Promise.all([
        getAllTopicSuggestions(),
        getTopicStatistics(),
        getResearchEngineStatus().catch(() => ({ available: false, enabled: false, running: false }))
      ]);

      const topicsData = topicsResponse.topic_suggestions || [];
      setTopics(topicsData);
      setStats(statsResponse || {});
      setActiveTopicsCount(
        topicsData.filter(topic => topic.is_active_research).length
      );
      setResearchEngineStatus(engineStatus);

    } catch (err) {
      console.error('Error loading topics data:', err);
      setError('Failed to load topics. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle global research engine toggle
  const handleToggleGlobalResearch = async () => {
    if (!researchEngineStatus) return;

    try {
      setResearchEngineLoading(true);

      if (researchEngineStatus.running) {
        await stopResearchEngine();
        setResearchEngineStatus(prev => ({ ...prev, running: false }));
      } else {
        await startResearchEngine();
        setResearchEngineStatus(prev => ({ ...prev, running: true }));
      }

    } catch (err) {
      console.error('Error toggling research engine:', err);
      setError('Failed to toggle research engine. Please try again.');
      // Refresh status to get correct state
      loadData();
    } finally {
      setResearchEngineLoading(false);
    }
  };

  // Handle immediate research trigger
  const handleImmediateResearch = async () => {
    if (!userId || immediateResearchLoading) return;

    try {
      setImmediateResearchLoading(true);
      setError(null);

      const result = await triggerManualResearch(userId);

      if (result.success) {
        const topicsResearched = result.topics_researched || 0;
        if (topicsResearched > 0) {
          // Refresh data to show any updates
          await loadData();
        } else {
          setError('No active research topics found to research');
        }
      } else {
        setError('Research trigger failed: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error triggering immediate research:', error);
      setError('Failed to trigger research. Please try again.');
    } finally {
      setImmediateResearchLoading(false);
    }
  };

  // Helper: base sorter according to filters
  const baseSorter = useCallback((a, b) => {
    let comparison = 0;
    switch (filters.sortBy) {
      case 'confidence':
        comparison = a.confidence_score - b.confidence_score;
        break;
      case 'date':
        comparison = a.suggested_at - b.suggested_at;
        break;
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      default:
        comparison = 0;
    }
    return filters.sortOrder === 'desc' ? -comparison : comparison;
  }, [filters.sortBy, filters.sortOrder]);

  // Filter and sort topics (with optional parent grouping)
  const filteredAndSortedTopics = React.useMemo(() => {
    let filtered = topics.filter(topic => {
      // Search filter
      if (filters.searchTerm) {
        const searchLower = filters.searchTerm.toLowerCase();
        if (!topic.name.toLowerCase().includes(searchLower) &&
            !topic.description.toLowerCase().includes(searchLower)) {
          return false;
        }
      }
      // Auto expansions only filter
      if (filters.autoOnly && !topic.is_child) {
        return false;
      }
      
      return true;
    });

    // Filter out children if their parent is not expanded
    filtered = filtered.filter(topic => {
      if (topic.is_child && topic.parent_id) {
        const parentExists = topics.some(t => t.topic_id === topic.parent_id);
        return parentExists && expandedParents.has(topic.parent_id);
      }
      return true;
    });

    // When grouping by parent, arrange topics so each parent is followed by its children
    if (filters.groupBy === 'parent') {
      // Map by topic_id for quick lookup
      const byId = new Map(filtered.map(t => [t.topic_id, t]));

      // Build children adjacency map using parent_id
      const childrenMap = new Map();
      filtered.forEach(t => {
        if (t.is_child && t.parent_id) {
          const arr = childrenMap.get(t.parent_id) || [];
          arr.push(t);
          childrenMap.set(t.parent_id, arr);
        }
      });

      // Sort children lists using the base sorter
      childrenMap.forEach(arr => arr.sort(baseSorter));

      // Identify roots: items that are not children or whose parent is not present
      const roots = filtered.filter(t => !t.is_child || !t.parent_id || !byId.has(t.parent_id));
      roots.sort(baseSorter);

      const ordered = [];
      const pushed = new Set();
      
      const visit = (node) => {
        if (!node || pushed.has(node.topic_id)) return;
        
        ordered.push(node);
        pushed.add(node.topic_id);
        
        // Only add children if parent is expanded (already filtered above, but double-check)
        const children = childrenMap.get(node.topic_id) || [];
        if (children.length > 0 && expandedParents.has(node.topic_id)) {
          children.forEach(child => visit(child));
        }
      };
      
      roots.forEach(visit);

      // Append any orphans not visited (cycles or missing roots)
      filtered.forEach(t => {
        if (!pushed.has(t.topic_id)) {
          ordered.push(t);
        }
      });

      return ordered;
    }

    // Default flat sorting
    return filtered.sort(baseSorter);
  }, [topics, filters, expandedParents, baseSorter]);

  // Handle topic selection
  const handleTopicSelect = (sessionId, topicIndex, selected) => {
    const topicKey = `${sessionId}-${topicIndex}`;
    const newSelected = new Set(selectedTopics);

    if (selected) {
      newSelected.add(topicKey);
    } else {
      newSelected.delete(topicKey);
    }

    setSelectedTopics(newSelected);
  };

  // Handle select all
  const handleSelectAll = () => {
    if (selectedTopics.size === filteredAndSortedTopics.length) {
      // Deselect all
      setSelectedTopics(new Set());
    } else {
      // Select all visible topics
      const allKeys = new Set();
      filteredAndSortedTopics.forEach((topic, index) => {
        allKeys.add(`${topic.session_id}-${index}`);
      });
      setSelectedTopics(allKeys);
    }
  };

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (selectedTopics.size === 0) return;

    if (!window.confirm(`Delete ${selectedTopics.size} selected topics?`)) {
      return;
    }

    try {
      setLoading(true);

      // Group selected topics by session
      const sessionGroups = {};
      filteredAndSortedTopics.forEach((topic, index) => {
        const topicKey = `${topic.session_id}-${index}`;
        if (selectedTopics.has(topicKey)) {
          if (!sessionGroups[topic.session_id]) {
            sessionGroups[topic.session_id] = [];
          }
          sessionGroups[topic.session_id].push(topic);
        }
      });

      // Count total topics per session
      const totalBySession = {};
      topics.forEach((topic) => {
        totalBySession[topic.session_id] = (totalBySession[topic.session_id] || 0) + 1;
      });

      const deletionPromises = [];
      for (const [sessionId, sessionTopics] of Object.entries(sessionGroups)) {
        if (sessionTopics.length === totalBySession[sessionId]) {
          // All topics from this session selected - delete entire session
          deletionPromises.push(deleteSessionTopics(sessionId));
        } else {
          // Delete individual topics by ID
          sessionTopics.forEach((topic) => {
            deletionPromises.push(deleteTopicById(topic.topic_id));
          });
        }
      }

      await Promise.all(deletionPromises);

      // Clear selection and reload data
      setSelectedTopics(new Set());
      await loadData();

    } catch (err) {
      console.error('Error deleting topics:', err);
      setError('Failed to delete topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle cleanup
  const handleCleanup = async () => {
    if (!window.confirm('Clean up old and duplicate topics? This action cannot be undone.')) {
      return;
    }

    try {
      setLoading(true);
      await cleanupTopics();
      await loadData();
    } catch (err) {
      console.error('Error cleaning up topics:', err);
      setError('Failed to clean up topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle delete non-activated topics
  const handleDeleteNonActivated = async () => {
    const nonActivatedCount = topics.filter(topic => !topic.is_active_research).length;

    if (nonActivatedCount === 0) {
      setError('No inactive topics found to delete.');
      return;
    }

    if (!window.confirm(`Delete all ${nonActivatedCount} topics that are not activated for research? This action cannot be undone.`)) {
      return;
    }

    try {
      setLoading(true);
      const result = await deleteNonActivatedTopics();

      if (result.success) {
        await loadData(); // Reload to reflect changes
        // Clear any previous error message
        setError(null);
      } else {
        setError('Failed to delete inactive topics. Please try again.');
      }
    } catch (err) {
      console.error('Error deleting non-activated topics:', err);
      setError('Failed to delete inactive topics. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle showing add topic form
  const handleShowAddTopicForm = () => {
    setShowAddTopicForm(true);
  };

  // Handle closing add topic form
  const handleCloseAddTopicForm = () => {
    setShowAddTopicForm(false);
  };

  // Handle topic added successfully
  const handleTopicAdded = (newTopic) => {
    // Refresh data to show the new topic
    loadData();

    // Update active topics count if the topic was created with research enabled
    if (newTopic.is_active_research) {
      setActiveTopicsCount(prev => prev + 1);
    }

    // Clear any previous error messages
    setError(null);
  };

  // Handle individual topic deletion
  const handleDeleteTopic = async (topicId, topicName) => {
    if (!window.confirm(`Delete topic "${topicName}"?`)) {
      return;
    }

    try {
      await deleteTopicById(topicId);  // Use safe ID-based deletion
      await loadData();  // Reload to reflect changes
    } catch (err) {
      console.error('Error deleting topic:', err);
      setError('Failed to delete topic. Please try again.');
    }
  };

  // Handle enabling research for a topic
  const handleEnableResearch = async (topic) => {
    if (!topic.topic_id) {
      console.error('Topic missing topic_id:', topic.name || 'Unknown topic');
      setError('Topic ID is missing. Please refresh the page and try again.');
      return;
    }

    // Validate UUID format (basic check)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (typeof topic.topic_id === 'string' && !uuidRegex.test(topic.topic_id)) {
      console.error('Invalid topic_id format (not a UUID):', topic.topic_id, 'for topic:', topic.name || 'Unknown');
      setError('Topic ID format is invalid. This topic may need to be recreated.');
      return;
    }

    try {
      // Optimistically update the UI and active count first
      setTopics(prevTopics =>
        prevTopics.map(t =>
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: true }
            : t
        )
      );
      setActiveTopicsCount(prev => prev + 1);

      // Use the new safe ID-based API instead of index-based
      await enableTopicResearchById(topic.topic_id);

      // Refresh data to ensure UI is in sync with backend state
      setTimeout(() => loadData(), 500);
    } catch (error) {
      // Only log error message, not full error object or response data
      const errorMsg = error.response?.data?.detail?.error || error.response?.data?.detail || error.message || 'Unknown error';
      console.error('Error enabling research for topic:', topic.name || topic.topic_id, '-', errorMsg);

      // Revert optimistic update on error
      setTopics(prevTopics =>
        prevTopics.map(t =>
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: false }
            : t
        )
      );
      setActiveTopicsCount(prev => Math.max(0, prev - 1));

      let errorMessage = 'Failed to enable research. Please try again.';

      // Extract error message from response
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'object' && detail.error) {
          errorMessage = detail.error;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      }

      setError(errorMessage);

      // Delay refresh slightly so error modal can display first
      // This ensures users can see the error message before the UI refreshes
      setTimeout(() => loadData(), 200);
    }
  };

  // Handle disabling research for a topic
  const handleDisableResearch = async (topic) => {
    if (!topic.topic_id) {
      console.error('Topic missing topic_id:', topic.name || 'Unknown topic');
      setError('Topic ID is missing. Please refresh the page and try again.');
      return;
    }

    // Validate UUID format (basic check)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (typeof topic.topic_id === 'string' && !uuidRegex.test(topic.topic_id)) {
      console.error('Invalid topic_id format (not a UUID):', topic.topic_id, 'for topic:', topic.name || 'Unknown');
      setError('Topic ID format is invalid. This topic may need to be recreated.');
      return;
    }

    try {
      // Optimistically update the UI and active count first
      setTopics(prevTopics =>
        prevTopics.map(t =>
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: false }
            : t
        )
      );
      setActiveTopicsCount(prev => Math.max(0, prev - 1));

      // Use the new safe ID-based API instead of index-based
      await disableTopicResearchById(topic.topic_id);

      // Refresh data to ensure UI is in sync with backend state
      // This is important because the research cycle may be running
      setTimeout(() => loadData(), 500);
    } catch (error) {
      // Only log error message, not full error object or response data
      const errorMsg = error.response?.data?.detail?.error || error.response?.data?.detail || error.message || 'Unknown error';
      console.error('Error disabling research for topic:', topic.name || topic.topic_id, '-', errorMsg);
      
      // Revert optimistic update on error
      setTopics(prevTopics =>
        prevTopics.map(t =>
          t.topic_id === topic.topic_id
            ? { ...t, is_active_research: true }
            : t
        )
      );
      setActiveTopicsCount(prev => prev + 1);
      
      // Extract error message for user display
      let errorMessage = 'Failed to disable research. Please try again.';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'object' && detail.error) {
          errorMessage = detail.error;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      }
      setError(errorMessage);
      // Delay refresh slightly so error modal can display first
      // This ensures users can see the error message before the UI refreshes
      setTimeout(() => loadData(), 200);
    }
  };

  // Handle topic expansion
  const toggleTopic = (topicKey) => {
    const newExpandedTopics = new Set(expandedTopics);
    if (newExpandedTopics.has(topicKey)) {
      newExpandedTopics.delete(topicKey);
    } else {
      newExpandedTopics.add(topicKey);
    }
    setExpandedTopics(newExpandedTopics);
  };

  // Toggle parent expansion to show/hide children
  const toggleParent = (topicId) => {
    const newExpandedParents = new Set(expandedParents);
    if (newExpandedParents.has(topicId)) {
      newExpandedParents.delete(topicId);
    } else {
      newExpandedParents.add(topicId);
    }
    setExpandedParents(newExpandedParents);
  };

  if (loading && topics.length === 0) {
    return (
      <div className="topics-dashboard">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading topics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="topics-dashboard">
      <TopicsHeader
        stats={stats}
        selectedCount={selectedTopics.size}
        totalCount={filteredAndSortedTopics.length}
        onCleanup={handleCleanup}
        onBulkDelete={handleBulkDelete}
        onSelectAll={handleSelectAll}
        loading={loading}
        researchEngineStatus={researchEngineStatus}
        onToggleGlobalResearch={handleToggleGlobalResearch}
        researchEngineLoading={researchEngineLoading}
        activeTopicsCount={activeTopicsCount}
        onImmediateResearch={handleImmediateResearch}
        immediateResearchLoading={immediateResearchLoading}
        onShowMotivation={() => setShowMotivation(true)}
        onShowEngineSettings={() => setShowEngineSettings(true)}
        onDeleteNonActivated={handleDeleteNonActivated}
        onAddCustomTopic={handleShowAddTopicForm}
        isAdmin={isAdmin}
      />

      <ErrorModal
        isOpen={!!error}
        message={error}
        onClose={() => setError(null)}
      />

      <TopicsFilters
        filters={filters}
        onFiltersChange={setFilters}
        topicsCount={filteredAndSortedTopics.length}
      />

      <div className="topics-content">
        {filteredAndSortedTopics.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📚</div>
            <h3>No Topics Found</h3>
            <p>
              {topics.length === 0
                ? "You haven't generated any research topics yet. Start chatting to discover interesting topics!"
                : "No topics match your current filters. Try adjusting your search criteria."
              }
            </p>
          </div>
        ) : (
          <div className="topics-list">
            {filteredAndSortedTopics.map((topic, index) => {
              const topicKey = `${topic.session_id}-${index}`;
              const isSelected = selectedTopics.has(topicKey);
              const isExpanded = expandedTopics.has(topicKey);
              // Calculate depth based on parent_id chain (simplified - just check if it's a child)
              const depth = topic && topic.is_child ? 1 : 0;
              
              // Find parent topic if this is a child
              const parentTopic = topic.is_child && topic.parent_id 
                ? topics.find(t => t.topic_id === topic.parent_id)
                : null;
              
              // Check if this is a parent (has children)
              const hasChildren = topics.some(t => t.parent_id === topic.topic_id);

              return (
                <div
                  key={topicKey}
                  className={`topic-item ${isSelected ? 'selected' : ''} ${topic.is_active_research ? 'active-research' : ''} ${depth > 0 ? 'child-topic' : 'root-topic'} ${hasChildren ? 'has-children' : ''} depth-${depth}`}
                  style={{ '--depth-indent': `${Math.min(depth, 6) * 24}px` }}
                >
                  <div
                    className="topic-header"
                    onClick={() => toggleTopic(topicKey)}
                  >
                    {/* Visual tree connector for child topics */}
                    {topic.is_child && (
                      <div className="topic-tree-connector">
                        <div className="tree-line-vertical"></div>
                        <div className="tree-line-horizontal"></div>
                      </div>
                    )}
                    
                    <div className="topic-info">
                      <div className="topic-title-row">
                        {topic.is_child && (
                          <span className="child-indicator" aria-label="Child topic">
                            ↳
                          </span>
                        )}
                        {hasChildren && !topic.is_child && (
                          <span className="parent-indicator" aria-label="Parent topic">
                            📁
                          </span>
                        )}
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleTopicSelect(topic.session_id, index, e.target.checked);
                          }}
                          className="topic-checkbox"
                        />
                        <h3 className="topic-name">{topic.name}</h3>
                        {topic.is_child && (
                          <span className="auto-badge" aria-label="Auto expansion">
                            <span className="badge-icon">🔗</span>
                            <span className="badge-text">Child</span>
                          </span>
                        )}
                        {hasChildren && !topic.is_child && (() => {
                          const childCount = topics.filter(t => t.parent_id === topic.topic_id).length;
                          return (
                            <span 
                              className="parent-badge" 
                              aria-label={`Has ${childCount} child topic${childCount !== 1 ? 's' : ''}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleParent(topic.topic_id);
                              }}
                              title={`${expandedParents.has(topic.topic_id) ? 'Hide' : 'Show'} ${childCount} child topic${childCount !== 1 ? 's' : ''}`}
                            >
                              <span className="badge-icon">📚</span>
                              <span className="badge-text">
                                {childCount} {childCount === 1 ? 'child' : 'children'} topic{childCount !== 1 ? 's' : ''}
                              </span>
                              <span className="badge-expand-icon">{expandedParents.has(topic.topic_id) ? '▼' : '▶'}</span>
                            </span>
                          );
                        })()}
                        {topic.is_active_research && (
                          <span className="research-status-badge">
                            <span className="badge-icon">🔬</span>
                            <span className="badge-text">RESEARCHING</span>
                          </span>
                        )}
                        {topic.expansion_status === 'paused' && (
                          <span className="expansion-status paused" aria-label="Expansion status: Paused">Paused</span>
                        )}
                        {topic.expansion_status === 'retired' && (
                          <span className="expansion-status retired" aria-label="Expansion status: Retired">Retired</span>
                        )}
                      </div>
                      <div className="topic-stats">
                        <span className="confidence-score">
                          Confidence: {(topic.confidence_score * 100).toFixed(0)}%
                        </span>
                        <span className="topic-date">
                          {formatDate(topic.suggested_at)}
                        </span>
                        {topic.session_id && (
                          <span className="session-info">
                            Session: {topic.session_id.substring(0, 8)}...
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="topic-toggle">
                      <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                        ▼
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="topic-details">
                      <div className="topic-description">
                        <h4>Description</h4>
                        <p>{topic.description}</p>
                      </div>

                      {topic.conversation_context && (
                        <div className="topic-context">
                          <h4>Context</h4>
                          <p className="context-text">"{topic.conversation_context}"</p>
                        </div>
                      )}

                      <div className="topic-actions">
                        {!topic.is_active_research ? (
                          <button
                            className="research-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEnableResearch(topic);
                            }}
                            title="Start researching this topic"
                          >
                            <span className="btn-icon">🔬</span>
                            <span className="btn-text">Start Research</span>
                          </button>
                        ) : (
                          <button
                            className="stop-research-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDisableResearch(topic);
                            }}
                            title="Stop researching this topic"
                          >
                            <span className="btn-icon">⏹️</span>
                            <span className="btn-text">Stop Research</span>
                          </button>
                        )}

                        <button
                          className="delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteTopic(topic.topic_id, topic.name);
                          }}
                          title="Delete this topic"
                        >
                          <span className="btn-icon">🗑️</span>
                          <span className="btn-text">Delete</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showMotivation && (
        <MotivationStats onClose={() => setShowMotivation(false)} />
      )}

      {showEngineSettings && (
        <EngineSettings onClose={() => setShowEngineSettings(false)} />
      )}

      {showAddTopicForm && (
        <AddTopicForm
          isOpen={showAddTopicForm}
          onClose={handleCloseAddTopicForm}
          onTopicAdded={handleTopicAdded}
        />
      )}
    </div>
  );
};

export default TopicsDashboard;
