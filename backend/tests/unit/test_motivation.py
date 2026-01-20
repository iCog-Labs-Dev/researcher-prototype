"""
Tests for the new database-backed motivation system.
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from services.motivation import MotivationSystem
from database.motivation_repository import MotivationRepository
from models.motivation import TopicScore, MotivationConfig
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager
from services.personalization_manager import PersonalizationManager


@pytest.fixture
async def mock_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
async def mock_profile_manager():
    """Mock profile manager."""
    manager = MagicMock(spec=ProfileManager)
    manager.list_users.return_value = ["test-user-123"]
    return manager


@pytest.fixture
async def mock_research_manager():
    """Mock research manager."""
    manager = MagicMock()  # Remove spec to allow any method
    manager.get_active_research_topics.return_value = [
        {
            "topic_name": "AI Research",
            "description": "Research about AI",
            "last_researched": 0,
            "staleness_coefficient": 1.0,
            "is_active_research": True
        }
    ]
    # Add the method that the tests need
    manager.get_topic_by_name.return_value = {
        "topic_name": "AI Research",
        "description": "Research about AI"
    }
    return manager


@pytest.fixture
async def motivation_system(mock_session):
    """Create motivation system with mocked dependencies."""
    return MotivationSystem(
        session=mock_session,
    )


@pytest.mark.asyncio
async def test_motivation_system_initialization(motivation_system):
    """Test that motivation system initializes correctly."""
    assert motivation_system.session is not None
    assert motivation_system.topic_service is not None
    assert motivation_system.research_service is not None
    assert motivation_system.is_running is False


@pytest.mark.asyncio
async def test_initialize_creates_default_config(motivation_system, mock_session):
    """Test that initialization creates default config if none exists."""
    # Mock database service to return no config initially
    with patch.object(motivation_system.db_service, 'get_default_config', return_value=None):
        with patch.object(motivation_system.db_service, 'create_default_config') as mock_create:
            mock_create.return_value = MagicMock(id=uuid.uuid4())
            
            await motivation_system.initialize()
            
            mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_update_scores_calculates_motivation(motivation_system, mock_session):
    """Test that update_scores calculates motivation for topics."""
    user_id = uuid.uuid4()
    
    # Expect a bulk UPDATE to be issued on the session
    with patch.object(motivation_system.session, 'execute', new_callable=AsyncMock) as mock_exec:
        # Provide config so update_scores doesn't early-return
        motivation_system._config = MagicMock(
            staleness_scale=0.0001,
            engagement_weight=0.3,
            quality_weight=0.2,
            topic_threshold=0.5,
        )

        # Stub session.query(...).group_by(...).cte('findings_agg')
        import sqlalchemy as sa
        from sqlalchemy.sql import column

        class _Cols:
            def __init__(self):
                # Real SQLA column constructs to satisfy type expectations
                self.user_id = column('user_id')
                self.topic_name = column('topic_name', sa.String())
                self.engagement_reads = column('engagement_reads', sa.Float())
                self.avg_quality = column('avg_quality', sa.Float())
                self.bookmarks = column('bookmarks', sa.Integer())
                self.integrations = column('integrations', sa.Integer())
                self.total = column('total', sa.Integer())

        class _CTE:
            def __init__(self):
                self.c = _Cols()

        class _QueryStub:
            def __init__(self, *args, **kwargs):
                pass
            def group_by(self, *args, **kwargs):
                return self
            def cte(self, *args, **kwargs):
                return _CTE()

        # The AsyncSession mock may not expose .query; inject attribute for this test
        setattr(motivation_system.session, 'query', lambda *a, **k: _QueryStub())
        # Provide the real sqlalchemy module to the target for type info
        import services.motivation as _mot_mod
        _mot_mod.sa = sa
        await motivation_system.update_scores()

        assert mock_exec.await_count >= 1


@pytest.mark.asyncio
async def test_check_for_research_needed_returns_true_when_topics_exist(motivation_system):
    """Test that check_for_research_needed returns True when motivated topics exist."""
    user_id = uuid.uuid4()

    # Mock config
    motivation_system._config = MagicMock()
    motivation_system._config.topic_threshold = 0.5

    # Mock topic service to return active topics
    mock_topic = MagicMock()
    mock_topic.user_id = user_id
    with patch.object(motivation_system.topic_service, 'async_get_active_research_topics', return_value=(True, [mock_topic])):
        # Mock database service to return topics needing research
        with patch.object(motivation_system.db_service, 'get_topics_needing_research', return_value=[mock_topic]):
            result = await motivation_system.check_for_research_needed()
            assert result is True


@pytest.mark.asyncio
async def test_check_for_research_needed_returns_false_when_no_topics(motivation_system):
    """Test that check_for_research_needed returns False when no motivated topics exist."""
    user_id = uuid.uuid4()

    # Mock config
    motivation_system._config = MagicMock()
    motivation_system._config.topic_threshold = 0.5

    # Mock topic service to return active topics
    mock_topic = MagicMock()
    mock_topic.user_id = user_id
    with patch.object(motivation_system.topic_service, 'async_get_active_research_topics', return_value=(True, [mock_topic])):
        # Mock database service to return no topics needing research
        with patch.object(motivation_system.db_service, 'get_topics_needing_research', return_value=[]):
            result = await motivation_system.check_for_research_needed()
            assert result is False


@pytest.mark.asyncio
async def test_calculate_topic_motivation_score_prioritizes_new_topics(motivation_system):
    """Test that new topics (never researched) get highest priority."""
    topic = {"topic_name": "New Topic", "last_researched": 0}
    
    # Mock config
    motivation_system._config = MagicMock()
    motivation_system._config.staleness_scale = 0.0001
    motivation_system._config.engagement_weight = 0.3
    motivation_system._config.quality_weight = 0.2
    
    with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.5):
        with patch.object(motivation_system, '_get_topic_success_rate', return_value=0.6):
            score = await motivation_system._calculate_topic_motivation_score("user123", topic)
            
            # New topics should get priority score of 1.0
            assert score == 1.0


@pytest.mark.asyncio
async def test_calculate_topic_motivation_score_calculates_staleness(motivation_system):
    """Test that previously researched topics get staleness-based scores."""
    import time
    current_time = time.time()
    user_id = str(uuid.uuid4())
    topic_id = uuid.uuid4()
    topic = {
        "topic_name": "Old Topic",
        "topic_id": str(topic_id),
        "last_researched": current_time - 3600,  # 1 hour ago
        "staleness_coefficient": 1.0
    }

    # Mock config
    motivation_system._config = MagicMock()
    motivation_system._config.staleness_scale = 0.0001
    motivation_system._config.engagement_weight = 0.3
    motivation_system._config.quality_weight = 0.2

    with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.5):
        with patch.object(motivation_system, '_get_topic_success_rate', return_value=0.6):
            score = await motivation_system._calculate_topic_motivation_score(user_id, topic)

            # Should be greater than 0 (staleness + engagement + quality)
            assert score > 0


@pytest.mark.asyncio
async def test_get_motivation_statistics_returns_user_stats(motivation_system):
    """Test that get_motivation_statistics returns user statistics."""
    user_id = str(uuid.uuid4())  # Use valid UUID string
    
    # Mock database service
    mock_stats = {
        'total_topics': 5,
        'active_topics': 3,
        'average_motivation_score': 0.7,
        'average_engagement_score': 0.6,
        'average_success_rate': 0.8,
        'total_findings': 25,
        'read_findings': 20,
        'engagement_rate': 0.8
    }
    
    with patch.object(motivation_system.db_service, 'get_motivation_statistics', return_value=mock_stats):
        stats = await motivation_system.get_motivation_statistics(user_id)
        
        assert stats['total_topics'] == 5
        assert stats['active_topics'] == 3
        assert stats['average_motivation_score'] == 0.7
        assert stats['engagement_rate'] == 0.8


@pytest.mark.asyncio
async def test_get_status_returns_system_status(motivation_system):
    """Test that get_status returns current system status."""
    status = motivation_system.get_status()

    assert 'running' in status
    assert 'check_interval' in status
    assert 'quality_threshold' in status
    assert 'system_type' in status
    assert 'features' in status

    assert status['system_type'] == 'MotivationSystem'
    assert 'database_persistence' in status['features']
    assert 'per_topic_scoring' in status['features']
    assert 'integrated_research_loop' in status['features']
    assert 'engagement_based_motivation' in status['features']


@pytest.mark.asyncio
async def test_start_stop_lifecycle(motivation_system):
    """Test that start/stop methods work correctly."""
    # Initially not running
    assert motivation_system.is_running is False
    
    # Mock the research loop to avoid actual async loop
    with patch.object(motivation_system, '_motivation_research_loop'):
        with patch.object(motivation_system, 'initialize'):
            await motivation_system.start()
            assert motivation_system.is_running is True
            
            await motivation_system.stop()
            assert motivation_system.is_running is False


@pytest.mark.asyncio
async def test_motivation_research_loop_calls_update_and_check(motivation_system):
    """Test that the main research loop calls update_scores and check_for_research_needed."""
    motivation_system.is_running = True
    
    with patch.object(motivation_system, 'update_scores') as mock_update:
        with patch.object(motivation_system, 'check_for_research_needed', return_value=False):
            with patch.object(motivation_system, '_conduct_research_cycle'):
                # Mock asyncio.sleep to avoid actual sleep - first call succeeds, second raises
                call_count = 0
                def sleep_side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return  # First sleep succeeds
                    else:
                        raise Exception("Stop loop")  # Second sleep raises
                
                with patch('asyncio.sleep', side_effect=sleep_side_effect):
                    # The loop should call update_scores after first sleep
                    with pytest.raises(Exception, match="Stop loop"):
                        await motivation_system._motivation_research_loop()
                    
                    mock_update.assert_called()


@pytest.mark.asyncio
async def test_get_topic_engagement_score_calculates_engagement(motivation_system):
    """Test that engagement score is calculated based on user interactions."""
    import time
    from datetime import datetime
    user_id = str(uuid.uuid4())
    topic_id = uuid.uuid4()

    # Mock research findings
    mock_finding1 = MagicMock()
    mock_finding1.read = True
    mock_finding1.bookmarked = False
    mock_finding1.integrated = False
    mock_finding1.created_at = datetime.fromtimestamp(time.time() - 3600)  # 1 hour ago

    mock_finding2 = MagicMock()
    mock_finding2.read = True
    mock_finding2.bookmarked = True
    mock_finding2.integrated = False
    mock_finding2.created_at = datetime.fromtimestamp(time.time() - 7200)

    mock_finding3 = MagicMock()
    mock_finding3.read = False
    mock_finding3.bookmarked = False
    mock_finding3.integrated = False
    mock_finding3.created_at = datetime.fromtimestamp(time.time() - 10800)

    mock_findings = [mock_finding1, mock_finding2, mock_finding3]

    with patch.object(motivation_system.research_service, 'async_get_findings', return_value=(True, mock_findings)):
        score = await motivation_system._get_topic_engagement_score(user_id, topic_id)

        # Should have some engagement score based on read findings
        assert score >= 0.0
        assert score <= 2.0  # Max engagement score


@pytest.mark.asyncio
async def test_get_topic_success_rate_returns_engagement_based_rate(motivation_system):
    """Test that success rate is calculated based on engagement."""
    user_id = str(uuid.uuid4())
    topic_id = uuid.uuid4()

    with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.8):
        success_rate = await motivation_system._get_topic_success_rate(user_id, topic_id)

        # Success rate should be in range 0.3-0.7 based on engagement
        assert 0.3 <= success_rate <= 0.7


@pytest.mark.asyncio
async def test_conduct_research_cycle_processes_motivated_topics(motivation_system):
    """Test that research cycle processes topics that need research."""
    user_id = uuid.uuid4()

    # Mock config
    motivation_system._config = MagicMock()
    motivation_system._config.topic_threshold = 0.5

    # Mock topic score that needs research
    mock_topic_score = MagicMock()
    mock_topic_score.topic_name = "AI Research"

    # Mock session to return user ids
    mock_result = MagicMock()
    mock_result.all.return_value = [(user_id,)]
    motivation_system.session.execute = AsyncMock(return_value=mock_result)

    # Mock topic from topic_service
    mock_topic = MagicMock()
    mock_topic.id = uuid.uuid4()
    mock_topic.name = "AI Research"
    mock_topic.description = "Research about AI"
    mock_topic.is_active_research = True
    mock_topic.last_researched = None

    # Mock database service
    with patch.object(motivation_system.db_service, 'get_topics_needing_research', return_value=[mock_topic_score]):
        with patch.object(motivation_system.topic_service, 'get_active_research_topics_by_user_id', return_value=[mock_topic]):
            with patch('services.autonomous_research_engine.get_autonomous_researcher') as gar:
                instance = MagicMock()
                instance.run_langgraph_research = AsyncMock(return_value={"success": True, "stored": True, "quality_score": 0.8})
                instance.process_expansions_for_root = AsyncMock(return_value=[])
                gar.return_value = instance
                with patch.object(motivation_system.db_service, 'create_or_update_topic_score'):
                    with patch('services.motivation.SessionLocal'):
                        result = await motivation_system._conduct_research_cycle()

                        assert result["topics_researched"] >= 0
                        assert "average_quality" in result


@pytest.mark.asyncio
async def test_research_topic_with_langgraph_invokes_research_workflow():
    """Test that the LangGraph helper is invoked and returns expected structure."""
    user_id = str(uuid.uuid4())
    topic = {
        "topic_name": "AI Research",
        "description": "Research about AI",
        "last_researched": 0
    }

    # Call the instance helper
    with patch('services.autonomous_research_engine.research_graph') as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={
            "module_results": {
                "research_storage": {
                    "success": True,
                    "stored": True,
                    "quality_score": 0.85,
                    "finding_id": "test-finding-123",
                    "insights_count": 3
                }
            }
        })
        from services.autonomous_research_engine import initialize_autonomous_researcher
        researcher = initialize_autonomous_researcher()
        result = await researcher.run_langgraph_research(user_id, topic)
        assert result["success"] is True
        assert result["stored"] is True
        assert result["quality_score"] >= 0.7
        assert result["finding_id"] is not None


@pytest.mark.asyncio
async def test_on_research_completed_handles_quality_score(motivation_system):
    """Test that research completion handler processes quality scores."""
    quality_score = 0.85
    
    # Should not raise any exceptions
    await motivation_system._on_research_completed(quality_score)


@pytest.mark.asyncio
async def test_initialize_handles_existing_config_and_state(motivation_system):
    """Test that initialization works when config and state already exist."""
    # Mock existing config and state
    mock_config = MagicMock()
    mock_state = MagicMock()
    
    with patch.object(motivation_system.db_service, 'get_default_config', return_value=mock_config):
        await motivation_system.initialize()
        assert motivation_system._config == mock_config


@pytest.mark.asyncio
async def test_initialize_handles_errors_gracefully(motivation_system):
    """Test that initialization raises errors when database operations fail."""
    with patch.object(motivation_system.db_service, 'get_default_config', side_effect=Exception("Database error")):
        with pytest.raises(Exception, match="Database error"):
            await motivation_system.initialize()


@pytest.mark.asyncio
async def test_start_prevents_double_start(motivation_system):
    """Test that start method prevents starting when already running."""
    motivation_system.is_running = True
    
    with patch.object(motivation_system, 'initialize') as mock_init:
        await motivation_system.start()
        
        # Should not call initialize when already running
        mock_init.assert_not_called()


@pytest.mark.asyncio
async def test_stop_handles_no_running_task(motivation_system):
    """Test that stop method handles case when no task is running."""
    motivation_system.is_running = False
    motivation_system.research_task = None
    
    # Should not raise any exceptions
    await motivation_system.stop()


@pytest.mark.asyncio
async def test_update_scores_handles_guest_user_gracefully(motivation_system):
    """Test that update_scores handles gracefully when no config is set."""
    motivation_system._config = None

    with patch.object(motivation_system.session, 'execute', new_callable=AsyncMock) as mock_exec:
        await motivation_system.update_scores()

        # Should not call execute when no config
        mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_research_needed_handles_invalid_users(motivation_system):
    """Test that check_for_research_needed handles invalid user IDs."""
    motivation_system._config = MagicMock()
    motivation_system._config.topic_threshold = 0.5

    # Mock topic service to return empty list
    with patch.object(motivation_system.topic_service, 'async_get_active_research_topics', return_value=(True, [])):
        # Should not raise exceptions and return False when no active topics
        result = await motivation_system.check_for_research_needed()
        assert result is False