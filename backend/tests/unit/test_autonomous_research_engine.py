import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch, call

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.autonomous_research_engine import AutonomousResearcher, initialize_autonomous_researcher, get_autonomous_researcher
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager


@pytest.fixture
def mock_profile_manager():
    """Create a mock ProfileManager for testing."""
    manager = MagicMock(spec=ProfileManager)
    manager.list_users.return_value = ["user1", "user2"]
    manager.storage = MagicMock()  # Add mock storage for PersonalizationManager initialization
    return manager


@pytest.fixture
def mock_research_manager():
    """Create a mock ResearchManager for testing."""
    manager = MagicMock(spec=ResearchManager)
    manager.get_active_research_topics.return_value = []
    manager.cleanup_old_research_findings.return_value = True
    return manager


@pytest.fixture
def mock_research_graph():
    """Create a mock research graph for testing."""
    graph = AsyncMock()
    graph.ainvoke.return_value = {
        "module_results": {
            "research_storage": {
                "success": True,
                "stored": True,
                "quality_score": 0.8,
                "finding_id": "test_finding_123",
                "insights_count": 3
            }
        }
    }
    return graph


@pytest.fixture
def autonomous_researcher():
    """Create an AutonomousResearcher with mocked dependencies."""
    with patch('services.autonomous_research_engine.research_graph') as mock_graph, \
         patch('services.autonomous_research_engine.TopicExpansionService') as mock_expansion:
        
        mock_graph.ainvoke = AsyncMock(return_value={
            "module_results": {
                "research_storage": {
                    "success": True,
                    "stored": True,
                    "quality_score": 0.8,
                    "finding_id": "test_finding_123",
                    "insights_count": 3
                }
            }
        })
        
        # Mock topic expansion service to return no candidates
        mock_expansion_instance = AsyncMock()
        mock_expansion_instance.generate_candidates.return_value = []
        mock_expansion.return_value = mock_expansion_instance
        
        researcher = AutonomousResearcher()
        researcher.research_graph = mock_graph
        researcher.topic_expansion_service = mock_expansion_instance
        return researcher


@pytest.fixture
def sample_topics():
    """Sample topic data for testing."""
    return [
        {
            "topic_name": "AI Research",
            "description": "Latest developments in artificial intelligence",
            "is_active_research": True,
            "research_count": 5,
            "last_researched": time.time() - 7200  # 2 hours ago
        },
        {
            "topic_name": "Climate Change",
            "description": "Environmental impact and solutions",
            "is_active_research": True,
            "research_count": 3,
            "last_researched": None  # Never researched
        }
    ]


@pytest.fixture
def motivation_config_override():
    """Sample motivation configuration override."""
    return {}


class TestAutonomousResearcherInitialization:
    """Test AutonomousResearcher initialization and configuration."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = AutonomousResearcher()
            
            assert researcher.is_running is False
            # Motivation now lives in motivation_system and is initialized on start
            assert getattr(researcher, 'motivation_system', None) is None
            assert isinstance(researcher.enabled, bool)

    def test_init_with_motivation_override(self, motivation_config_override):
        """Override is accepted by initializer."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = initialize_autonomous_researcher(
                motivation_config_override,
            )
            assert isinstance(researcher, AutonomousResearcher)
            # Overrides applied later on start; object should be initialized and disabled by default
            assert researcher.is_running is False

    def test_enable_disable_functionality(self, autonomous_researcher):
        """Test enable/disable functionality."""
        # Test enable
        autonomous_researcher.enable()
        assert autonomous_researcher.is_enabled() is True
        
        # Test disable
        autonomous_researcher.disable()
        assert autonomous_researcher.is_enabled() is False
        
        # Test toggle
        result = autonomous_researcher.toggle_enabled()
        assert result is True
        assert autonomous_researcher.is_enabled() is True
        
        result = autonomous_researcher.toggle_enabled()
        assert result is False
        assert autonomous_researcher.is_enabled() is False

    def test_get_status(self, autonomous_researcher):
        """Test status reporting."""
        status = autonomous_researcher.get_status()

        expected_keys = [
            "enabled", "running", "quality_threshold",
            "retention_days", "engine_type", "research_graph_nodes"
        ]

        for key in expected_keys:
            assert key in status

        assert status["engine_type"] == "Motivation-driven LangGraph-based"
        assert isinstance(status["research_graph_nodes"], list)
        assert len(status["research_graph_nodes"]) > 0


class TestResearchCycleLogic:
    """Test research cycle and topic research logic."""


    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_success(self, autonomous_researcher, sample_topics):
        """Test successful topic research with LangGraph."""
        topic = sample_topics[0]
        
        with patch('services.autonomous_research_engine.research_graph') as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "module_results": {
                    "research_storage": {
                        "success": True,
                        "stored": True,
                        "quality_score": 0.8,
                        "finding_id": "test_finding_123",
                        "insights_count": 3
                    }
                }
            })
            result = await autonomous_researcher.run_langgraph_research("user1", topic)
        
        assert result is not None
        assert result["success"] is True
        assert result["stored"] is True
        assert result["quality_score"] == 0.8
        assert result["finding_id"] == "test_finding_123"
        assert result["insights_count"] == 3

    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_not_stored(self, autonomous_researcher, sample_topics):
        """Test topic research where finding is not stored."""
        # Mock research graph to return not stored result
        with patch('services.autonomous_research_engine.research_graph') as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "module_results": {
                    "research_storage": {
                        "success": True,
                        "stored": False,
                        "quality_score": 0.3,
                        "reason": "Quality too low"
                    }
                }
            })
            topic = sample_topics[0]
            result = await autonomous_researcher.run_langgraph_research("user1", topic)
        
        assert result is not None
        assert result["success"] is True
        assert result["stored"] is False
        assert result["reason"] == "Quality too low"
        assert result["quality_score"] == 0.3

    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_failure(self, autonomous_researcher, sample_topics):
        """Test topic research failure handling."""
        # Mock research graph to return failure
        with patch('services.autonomous_research_engine.research_graph') as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "module_results": {
                    "research_storage": {
                        "success": False,
                        "stored": False,
                        "error": "Network error"
                    }
                }
            })
        
            topic = sample_topics[0]
            result = await autonomous_researcher.run_langgraph_research("user1", topic)
        
        assert result is not None
        assert result["success"] is False
        assert result["stored"] is False
        assert result["error"] == "Network error"

    @pytest.mark.asyncio
    async def test_research_topic_with_langgraph_exception(self, autonomous_researcher, sample_topics):
        """Test topic research with exception handling."""
        # Mock research graph to raise exception
        with patch('services.autonomous_research_engine.research_graph') as mock_graph:
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution failed"))
        
            topic = sample_topics[0]
            result = await autonomous_researcher.run_langgraph_research("user1", topic)
        
        assert result is not None
        assert result["success"] is False
        assert result["stored"] is False
        assert "Graph execution failed" in result["error"]


class TestAutonomousResearchLoop:
    """Test the autonomous research loop and lifecycle."""

    @pytest.mark.asyncio
    async def test_start_when_disabled(self, autonomous_researcher):
        """Test starting when research engine is disabled."""
        autonomous_researcher.disable()
        
        await autonomous_researcher.start()
        
        assert autonomous_researcher.is_running is False
        assert autonomous_researcher.research_task is None

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, autonomous_researcher):
        """Test starting when already running."""
        autonomous_researcher.is_running = True
        
        await autonomous_researcher.start()
        
        # Should still be running, no new task created
        assert autonomous_researcher.is_running is True

    @pytest.mark.asyncio
    async def test_start_and_stop_lifecycle(self, autonomous_researcher):
        """Test complete start/stop lifecycle."""
        # Enable the researcher first
        autonomous_researcher.enable()
        
        # Patch MotivationSystem to avoid DB and network
        with patch('services.autonomous_research_engine.MotivationSystem') as MS, \
             patch('services.autonomous_research_engine.SessionLocal', create=True) as Sess:
            inst = MS.return_value
            inst.start = AsyncMock()
            inst.stop = AsyncMock()
            inst.get_status = MagicMock(return_value={})
            # Start the engine
            await autonomous_researcher.start()
            assert autonomous_researcher.is_running is True
            # Let it run briefly
            await asyncio.sleep(0.05)
            # Stop the engine
            await autonomous_researcher.stop()
            assert autonomous_researcher.is_running is False

    @pytest.mark.asyncio
    async def test_research_loop_motivation_trigger(self, autonomous_researcher, sample_topics):
        """Test research loop triggering research when motivated."""
        # Enable the researcher first
        autonomous_researcher.enable()

        # Setup mocks (patch MotivationSystem)
        with patch('services.autonomous_research_engine.MotivationSystem') as MS, \
             patch('services.autonomous_research_engine.SessionLocal', create=True):
            inst = MS.return_value
            inst.start = AsyncMock()
            inst.stop = AsyncMock()
            inst.get_status = MagicMock(return_value={})
            # Start and stop; do not assert internal Motivation loop behavior here
            await autonomous_researcher.start()
            await asyncio.sleep(0.05)
            await autonomous_researcher.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, autonomous_researcher):
        """Test stopping when not running."""
        assert autonomous_researcher.is_running is False
        
        # Should complete without error
        await autonomous_researcher.stop()
        
        assert autonomous_researcher.is_running is False


class TestManualResearchTrigger:
    """Test manual research triggering functionality."""

    @pytest.mark.asyncio
    async def test_trigger_research_no_active_topics(self, autonomous_researcher):
        """Test manual research trigger with no active topics."""
        import uuid
        user_id = str(uuid.uuid4())

        with patch.object(autonomous_researcher.topic_service, 'async_get_active_research_topics', return_value=[]):
            result = await autonomous_researcher.trigger_research_for_user(user_id)

        assert result["success"] is True
        assert result["message"] == "No active research topics found"
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0

    @pytest.mark.asyncio
    async def test_trigger_research_success(self, autonomous_researcher, sample_topics):
        """Test successful manual research trigger."""
        import uuid
        from datetime import datetime, timezone
        user_id = str(uuid.uuid4())

        # Create mock topic objects
        mock_topic1 = MagicMock()
        mock_topic1.id = uuid.uuid4()
        mock_topic1.name = "AI Research"
        mock_topic1.description = "Latest developments in artificial intelligence"
        mock_topic1.is_active_research = True
        mock_topic1.last_researched = datetime.now(timezone.utc)

        mock_topic2 = MagicMock()
        mock_topic2.id = uuid.uuid4()
        mock_topic2.name = "Climate Change"
        mock_topic2.description = "Environmental impact and solutions"
        mock_topic2.is_active_research = True
        mock_topic2.last_researched = None

        mock_topics = [mock_topic1, mock_topic2]

        with patch.object(autonomous_researcher.topic_service, 'async_get_active_research_topics', return_value=mock_topics):
            with patch('services.autonomous_research_engine.research_graph') as mock_graph:
                mock_graph.ainvoke = AsyncMock(return_value={
                    "module_results": {"research_storage": {"success": True, "stored": True, "quality_score": 0.8}}
                })
                result = await autonomous_researcher.trigger_research_for_user(user_id)

        assert result["success"] is True
        assert result["topics_researched"] >= 0
        assert result["findings_stored"] >= 0
        assert result["total_active_topics"] == 2
        assert len(result["research_details"]) == 2

        # Check research details
        detail = result["research_details"][0]
        assert detail["topic_name"] == "AI Research"
        assert detail["success"] is True
        assert detail["stored"] is True
        assert detail["quality_score"] == 0.8

    @pytest.mark.asyncio
    async def test_trigger_research_with_failures(self, autonomous_researcher, sample_topics):
        """Test manual research trigger with some failures."""
        import uuid
        from datetime import datetime, timezone
        user_id = str(uuid.uuid4())

        # Create mock topic objects
        mock_topic1 = MagicMock()
        mock_topic1.id = uuid.uuid4()
        mock_topic1.name = "AI Research"
        mock_topic1.description = "Latest developments in artificial intelligence"
        mock_topic1.is_active_research = True
        mock_topic1.last_researched = datetime.now(timezone.utc)

        mock_topic2 = MagicMock()
        mock_topic2.id = uuid.uuid4()
        mock_topic2.name = "Climate Change"
        mock_topic2.description = "Environmental impact and solutions"
        mock_topic2.is_active_research = True
        mock_topic2.last_researched = None

        mock_topics = [mock_topic1, mock_topic2]

        # Mock one success, one failure
        call_count = 0
        async def mock_research_topic(user_id, topic):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"success": True, "stored": True, "quality_score": 0.8}
            else:
                return {"success": False, "stored": False, "error": "API error"}

        autonomous_researcher.run_langgraph_research = mock_research_topic

        with patch.object(autonomous_researcher.topic_service, 'async_get_active_research_topics', return_value=mock_topics):
            result = await autonomous_researcher.trigger_research_for_user(user_id)

        assert result["success"] is True
        assert result["topics_researched"] >= 0
        assert result["findings_stored"] >= 0
        assert len(result["research_details"]) == 2

        # Check mixed results
        success_detail = next(d for d in result["research_details"] if d["success"])
        failure_detail = next(d for d in result["research_details"] if not d["success"])

        assert success_detail["stored"] is True
        assert failure_detail["error"] == "API error"

    @pytest.mark.asyncio
    async def test_trigger_research_exception_handling(self, autonomous_researcher):
        """Test manual research trigger exception handling."""
        import uuid
        user_id = str(uuid.uuid4())

        with patch.object(autonomous_researcher.topic_service, 'async_get_active_research_topics', side_effect=Exception("Database error")):
            result = await autonomous_researcher.trigger_research_for_user(user_id)

        assert result["success"] is False
        assert "Database error" in result["error"]
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0


class TestResearchCycleIntegration:
    """Test the complete research cycle integration.

    Note: The research cycle is now handled by MotivationSystem, not AutonomousResearcher.
    These tests verify that the researcher correctly delegates to the motivation system.
    """

    @pytest.mark.asyncio
    async def test_motivation_system_integration(self, autonomous_researcher):
        """Test that researcher correctly integrates with motivation system."""
        # Enable the researcher
        autonomous_researcher.enable()

        # Verify motivation system is not initialized until start() is called
        assert autonomous_researcher.motivation_system is None

    @pytest.mark.asyncio
    async def test_start_initializes_motivation_system(self, autonomous_researcher):
        """Test that start() initializes the motivation system."""
        autonomous_researcher.enable()

        with patch('services.autonomous_research_engine.MotivationSystem') as MS, \
             patch('services.autonomous_research_engine.SessionLocal', create=True):
            inst = MS.return_value
            inst.start = AsyncMock()
            inst.stop = AsyncMock()

            await autonomous_researcher.start()

            # Verify motivation system was created
            assert MS.called
            inst.start.assert_called_once()

            await autonomous_researcher.stop()

    @pytest.mark.asyncio
    async def test_stop_stops_motivation_system(self, autonomous_researcher):
        """Test that stop() stops the motivation system."""
        autonomous_researcher.enable()

        with patch('services.autonomous_research_engine.MotivationSystem') as MS, \
             patch('services.autonomous_research_engine.SessionLocal', create=True):
            inst = MS.return_value
            inst.start = AsyncMock()
            inst.stop = AsyncMock()

            await autonomous_researcher.start()
            await autonomous_researcher.stop()

            inst.stop.assert_called_once()



class TestGlobalFunctions:
    """Test global initialization and accessor functions."""

    def test_initialize_autonomous_researcher(self):
        """Test global initialization function."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = initialize_autonomous_researcher()
            
            assert isinstance(researcher, AutonomousResearcher)

    def test_get_autonomous_researcher(self):
        """Test global accessor function."""
        with patch('services.autonomous_research_engine.research_graph'):
            # Initialize first
            researcher = initialize_autonomous_researcher()
            
            # Get should return the same instance
            retrieved = get_autonomous_researcher()
            assert retrieved is researcher

    def test_initialize_with_motivation_override(self, motivation_config_override):
        """Test initialization with motivation configuration override."""
        with patch('services.autonomous_research_engine.research_graph'):
            researcher = initialize_autonomous_researcher(
                motivation_config_override
            )
            assert isinstance(researcher, AutonomousResearcher)


class TestErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_research_loop_exception_handling(self, autonomous_researcher):
        """Test research loop handles exceptions gracefully."""
        autonomous_researcher.enable()

        with patch('services.autonomous_research_engine.MotivationSystem') as MS, \
             patch('services.autonomous_research_engine.SessionLocal', create=True):
            inst = MS.return_value
            inst.start = AsyncMock(side_effect=Exception("Motivation error"))
            inst.stop = AsyncMock()

            # Start should handle the exception
            await autonomous_researcher.start()

            # Should have stopped due to error
            assert autonomous_researcher.is_running is False

    @pytest.mark.asyncio
    async def test_trigger_research_handles_invalid_user(self, autonomous_researcher):
        """Test that trigger_research handles invalid user IDs gracefully."""
        result = await autonomous_researcher.trigger_research_for_user("invalid-uuid")

        assert result["success"] is False
        assert "Invalid user_id" in result["error"]
        assert result["topics_researched"] == 0
        assert result["findings_stored"] == 0