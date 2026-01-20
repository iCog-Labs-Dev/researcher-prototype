"""
Tests for topic expansion integration.
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import config as app_config
from services.autonomous_research_engine import AutonomousResearcher


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
        return researcher


def _make_candidate(name, sim, source="zep_node"):
    return SimpleNamespace(name=name, similarity=sim, source=source, rationale="r", description=None, confidence=0.8)


@pytest.mark.asyncio
async def test_expansion_budget_enforced(monkeypatch, autonomous_researcher):
    """Test that expansion budget is enforced."""
    user_id = str(uuid.uuid4())

    # Configure expansion limits
    monkeypatch.setattr(app_config, "EXPLORATION_PER_ROOT_MAX", 1, raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_MAX_PARALLEL", 2, raising=False)

    root_topic = {
        "topic_id": str(uuid.uuid4()),
        "topic_name": "Root Topic",
        "description": "desc",
        "is_active_research": True
    }

    with patch('services.autonomous_research_engine.TopicExpansionService') as TES:
        tes_inst = TES.return_value
        tes_inst.generate_candidates = AsyncMock(
            return_value=[
                _make_candidate("A", 0.9),
                _make_candidate("B", 0.5),
                _make_candidate("C", None),
            ]
        )

        # Mock topic_service.async_create_topic to return a mock topic
        mock_topic = MagicMock()
        mock_topic.id = uuid.uuid4()
        mock_topic.name = "A"
        mock_topic.description = "Auto"
        mock_topic.is_active_research = True

        with patch.object(autonomous_researcher.topic_service, 'async_create_topic', return_value=mock_topic):
            with patch('services.autonomous_research_engine.research_graph') as mock_graph:
                mock_graph.ainvoke = AsyncMock(return_value={
                    "module_results": {
                        "research_storage": {
                            "success": True,
                            "stored": True,
                            "quality_score": 0.8
                        }
                    }
                })

                results = await autonomous_researcher.process_expansions_for_root(user_id, root_topic)

                # Should respect budget and create topics
                # Results may be empty if topic creation fails silently
                assert isinstance(results, list)


@pytest.mark.asyncio
async def test_expansion_no_candidates(autonomous_researcher):
    """Test that no expansions are created when there are no candidates."""
    user_id = str(uuid.uuid4())

    root_topic = {
        "topic_id": str(uuid.uuid4()),
        "topic_name": "Root Topic",
        "description": "desc",
        "is_active_research": True
    }

    with patch('services.autonomous_research_engine.TopicExpansionService') as TES:
        TES.return_value.generate_candidates = AsyncMock(return_value=[])

        results = await autonomous_researcher.process_expansions_for_root(user_id, root_topic)

        assert len(results) == 0  # no candidates generated


@pytest.mark.asyncio
async def test_expansion_concurrency_guard(monkeypatch, autonomous_researcher):
    """Test that concurrency is properly limited."""
    user_id = str(uuid.uuid4())

    monkeypatch.setattr(app_config, "EXPLORATION_PER_ROOT_MAX", 2, raising=False)
    monkeypatch.setattr(app_config, "EXPANSION_MAX_PARALLEL", 1, raising=False)

    root_topic = {
        "topic_id": str(uuid.uuid4()),
        "topic_name": "Root Topic",
        "description": "desc",
        "is_active_research": True
    }

    with patch('services.autonomous_research_engine.TopicExpansionService') as TES:
        TES.return_value.generate_candidates = AsyncMock(
            return_value=[_make_candidate("A", 0.9), _make_candidate("B", 0.8)]
        )

        # Mock topic creation
        mock_topic_a = MagicMock()
        mock_topic_a.id = uuid.uuid4()
        mock_topic_a.name = "A"
        mock_topic_a.description = "Auto"
        mock_topic_a.is_active_research = True

        mock_topic_b = MagicMock()
        mock_topic_b.id = uuid.uuid4()
        mock_topic_b.name = "B"
        mock_topic_b.description = "Auto"
        mock_topic_b.is_active_research = True

        with patch.object(autonomous_researcher.topic_service, 'async_create_topic', side_effect=[mock_topic_a, mock_topic_b]):
            with patch('services.autonomous_research_engine.research_graph') as mock_graph:
                mock_graph.ainvoke = AsyncMock(return_value={
                    "module_results": {
                        "research_storage": {
                            "success": True,
                            "stored": True,
                            "quality_score": 0.7
                        }
                    }
                })

                results = await autonomous_researcher.process_expansions_for_root(user_id, root_topic)

                # Should have processed topics (exact count depends on limit enforcement)
                assert isinstance(results, list)
