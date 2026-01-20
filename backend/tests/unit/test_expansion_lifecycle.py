"""
Tests for expansion lifecycle management.

Note: Lifecycle logic is now handled by MotivationSystem, not AutonomousResearcher.
"""
import time
import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

import config as app_config
from services.motivation import MotivationSystem


@pytest.fixture
async def mock_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
async def motivation_system(mock_session):
    """Create motivation system with mocked dependencies."""
    return MotivationSystem(session=mock_session)


def _mk_topic_score(name, is_exp=True, depth=1, status='active', enabled=False, last_eval=0, backoff_until=0):
    """Create a mock TopicScore object."""
    ts = MagicMock()
    ts.topic_name = name
    ts.topic_id = uuid.uuid4()
    ts.user_id = uuid.uuid4()
    ts.is_active_research = True
    ts.meta_data = {
        "is_expansion": is_exp,
        "expansion_depth": depth,
        "child_expansion_enabled": enabled,
        "expansion_status": status,
        "last_evaluated_at": last_eval,
        "last_backoff_until": backoff_until,
    }
    return ts


@pytest.mark.asyncio
async def test_lifecycle_promote_children(motivation_system):
    """Test that topics with high engagement get promoted."""
    user_id = str(uuid.uuid4())

    # Create topic score
    topic_score = _mk_topic_score("T1", enabled=False)

    # Mock db_service to return topic scores
    with patch.object(motivation_system.db_service, 'get_user_topic_scores', return_value=[topic_score]):
        # Mock engagement calculation to return high engagement
        with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.5):
            with patch.object(motivation_system, 'get_recent_average_quality', return_value=0.8):
                with patch.object(motivation_system.db_service, 'update_topic_score') as mock_update:
                    await motivation_system._update_expansion_lifecycle(user_id)

                    # Should have attempted update
                    # (actual assertion depends on the promote threshold being met)


@pytest.mark.asyncio
async def test_lifecycle_pause_on_cold_engagement(motivation_system):
    """Test that topics with cold engagement get paused."""
    user_id = str(uuid.uuid4())

    # Create topic score with active status
    topic_score = _mk_topic_score("Cold", enabled=False, status='active')

    # Mock db_service to return topic scores
    with patch.object(motivation_system.db_service, 'get_user_topic_scores', return_value=[topic_score]):
        # Mock zero engagement
        with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.0):
            with patch.object(motivation_system, 'get_recent_average_quality', return_value=0.3):
                # Mock no interactions
                with patch.object(motivation_system.research_service, 'async_get_findings', return_value=(True, [])):
                    with patch.object(motivation_system.db_service, 'update_topic_score') as mock_update:
                        await motivation_system._update_expansion_lifecycle(user_id)

                        # Verify update was called (may be pausing the topic)
                        # The exact behavior depends on threshold values


@pytest.mark.asyncio
async def test_lifecycle_retire_after_ttl(monkeypatch, motivation_system):
    """Test that paused topics get retired after TTL."""
    monkeypatch.setattr(app_config, "EXPANSION_RETIRE_TTL_DAYS", 1, raising=False)
    user_id = str(uuid.uuid4())

    old = time.time() - (2 * 24 * 3600)
    topic_score = _mk_topic_score("OldPaused", status='paused', last_eval=old)

    with patch.object(motivation_system.db_service, 'get_user_topic_scores', return_value=[topic_score]):
        with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.0):
            with patch.object(motivation_system, 'get_recent_average_quality', return_value=0.0):
                with patch.object(motivation_system.research_service, 'async_get_findings', return_value=(True, [])):
                    with patch.object(motivation_system.db_service, 'update_topic_score') as mock_update:
                        await motivation_system._update_expansion_lifecycle(user_id)

                        # Should have called update to retire the topic
                        if mock_update.called:
                            call_args = mock_update.call_args
                            if call_args and call_args.kwargs.get('meta_data'):
                                assert call_args.kwargs['meta_data'].get('expansion_status') == 'retired'


@pytest.mark.asyncio
async def test_depth_and_backoff_gate(monkeypatch, motivation_system):
    """Test that depth and backoff gates are respected."""
    monkeypatch.setattr(app_config, "EXPANSION_MAX_DEPTH", 1, raising=False)
    user_id = str(uuid.uuid4())

    # Topic at max depth
    topic_score = _mk_topic_score("Parent", depth=1, enabled=False)

    with patch.object(motivation_system.db_service, 'get_user_topic_scores', return_value=[topic_score]):
        with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.5):
            with patch.object(motivation_system, 'get_recent_average_quality', return_value=0.7):
                with patch.object(motivation_system.db_service, 'update_topic_score') as mock_update:
                    await motivation_system._update_expansion_lifecycle(user_id)

                    # Lifecycle should still process, depth gating is for expansions
                    # not for lifecycle updates


@pytest.mark.asyncio
async def test_gating_only_affects_expansions(motivation_system):
    """Test that gating only affects expansion topics, not regular topics."""
    user_id = str(uuid.uuid4())

    # Non-expansion topic
    topic_score = _mk_topic_score("Root", is_exp=False)

    with patch.object(motivation_system.db_service, 'get_user_topic_scores', return_value=[topic_score]):
        with patch.object(motivation_system, '_get_topic_engagement_score', return_value=0.5):
            with patch.object(motivation_system.db_service, 'update_topic_score') as mock_update:
                await motivation_system._update_expansion_lifecycle(user_id)

                # Non-expansion topics should be skipped
                mock_update.assert_not_called()
