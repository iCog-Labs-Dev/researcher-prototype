from __future__ import annotations
import time
from uuid import UUID
from typing import Any, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from db import SessionLocal
from exceptions import NotFound, CommonError
from services.logging_config import get_logger
from models.user import User, UserProfile
from schemas.user import (
    PreferencesConfig,
    EngagementAnalytics,
    PersonalizationHistory,
    AdaptationLogEntry,
)

logger = get_logger(__name__)


class UserService:
    async def get_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        with_profile: bool = False,
    ) -> User:
        if with_profile:
            query = (
                select(User)
                .options(selectinload(User.profile))
                .where(User.id == user_id)
            )
            res = await session.execute(query)
            user = res.scalar_one_or_none()
        else:
            user = await session.get(User, user_id)

        if not user:
            raise NotFound("User not found")

        return user

    async def list_users(
        self,
        session: AsyncSession,
        limit: int,
        offset: int,
    ) -> list[User]:
        res = await session.execute(
            select(User)
            .options(selectinload(User.profile))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(res.scalars().all())

    async def async_get_personalization_context(
        self,
        user_id: Optional[str],
    ) -> dict[str, Any]:
        if not user_id:
            return {}

        try:
            async with SessionLocal() as session:
                profile = await session.get(UserProfile, user_id)

            if profile is None:
                logger.error(f"🔍 User {user_id} profile not found")
                return {}

            preferences = profile.preferences or {}
            analytics = profile.engagement_analytics or {}

            content_preferences = preferences.get("content_preferences") or {}
            format_preferences = preferences.get("format_preferences") or {}
            interaction_preferences = preferences.get("interaction_preferences") or {}

            learned_adaptations = analytics.get("learned_adaptations") or {}
            interaction_signals = analytics.get("interaction_signals") or {}

            preferred_sources = interaction_signals.get("most_engaged_source_types") or []
            follow_up_frequency = interaction_signals.get("follow_up_question_frequency") or 0.0

            return {
                "content_preferences": content_preferences,
                "format_preferences": format_preferences,
                "interaction_preferences": interaction_preferences,
                "learned_adaptations": learned_adaptations,
                "engagement_patterns": {
                    "preferred_sources": list(preferred_sources),
                    "follow_up_frequency": float(follow_up_frequency),
                },
            }
        except Exception as e:
            logger.error(f"🔍 Failed to get personalization context for user {user_id}: {str(e)}")
            return {}

    async def async_get_personality(
        self,
        user_id: Optional[str],
    ) -> dict[str, Any]:
        default_personality = {"style": "helpful", "tone": "friendly", "additional_traits": {}}

        if not user_id:
            return default_personality

        try:
            async with SessionLocal() as session:
                profile = await session.get(UserProfile, user_id)

            if profile is None:
                logger.error(f"🔍 User {user_id} profile not found")
                return default_personality

            if not profile.personality:
                return default_personality

            return profile.personality
        except Exception as e:
            logger.error(f"🔍 Failed to get personality for user {user_id}: {str(e)}")
            return default_personality

    async def update_display_name(
        self,
        session: AsyncSession,
        user_id: UUID,
        display_name: str,
    ) -> str:
        value = display_name.strip()
        if not value:
            raise CommonError("Display name cannot be empty")

        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        meta = profile.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}

        meta["display_name"] = value
        profile.meta_data = meta

        await session.commit()

        return user.profile.meta_data["display_name"]

    async def update_email(
        self,
        session: AsyncSession,
        user_id: UUID,
        email: str,
    ) -> str:
        value = email.strip().lower()
        if not value:
            raise CommonError("Email cannot be empty")

        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        meta = profile.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}

        meta["email"] = value
        profile.meta_data = meta

        await session.commit()

        return user.profile.meta_data["email"]

    async def update_preferences(
        self,
        session: AsyncSession,
        user_id: UUID,
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        profile.preferences = preferences
        await session.commit()

        return user.profile.preferences or {}

    async def update_personality(
        self,
        session: AsyncSession,
        user_id: UUID,
        personality: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        profile.personality = personality
        await session.commit()

        return user.profile.personality or {}

    async def update_role(
        self,
        session: AsyncSession,
        target_user_id: UUID,
        role: str,
    ) -> str:
        user = await self.get_user(session, target_user_id)

        user.role = role
        await session.commit()

        return user.role

    async def track_user_engagement(
        self,
        session: AsyncSession,
        profile: UserProfile,
        interaction_type: str,
        metadata: Dict[str, Any],
    ) -> None:
        preferences = self._load_preferences(profile)
        engagement_analytics = self._load_engagement_analytics(profile)
        personalization_history = self._load_personalization_history(profile)

        applied_preferences = False
        applied_engagement_analytics = False
        applied_personalization_history = False

        if interaction_type == "research_finding":
            source_types = metadata.get("source_types", [])
            feedback = metadata.get("feedback")
            link_clicks = int(metadata.get("link_clicks", 0))
            source_exploration = int(metadata.get("source_exploration_clicks", 0))
            session_continuation = float(metadata.get("session_continuation_rate", 0.0))
            content_length = int(metadata.get("content_length", 0))

            if source_types and feedback == "up":
                for st in source_types:
                    if st not in engagement_analytics.interaction_signals.most_engaged_source_types:
                        engagement_analytics.interaction_signals.most_engaged_source_types.append(st)
                        applied_engagement_analytics = True

            engagement_score = self._calc_engagement_score(feedback, link_clicks, source_exploration, session_continuation)

            source_prefs = dict(preferences.content_preferences.source_types or {})
            if engagement_score > 0.7 or engagement_score < 0.3:
                changes_made = {}

                for st in source_types:
                    if st in source_prefs:
                        old_value = source_prefs[st]
                        new_value = old_value

                        if engagement_score > 0.7:
                            new_value = max(0.1, min(1.0, old_value + 0.05))
                        elif engagement_score < 0.3:
                            new_value = max(0.1, min(1.0, source_prefs[st] - 0.03))

                        source_prefs[st] = new_value
                        changes_made[st] = {"old": old_value, "new": new_value}

                if changes_made:
                    preferences.content_preferences.source_types = source_prefs
                    applied_preferences = True

                    self._log_adaptation(
                        personalization_history,
                        "source_preference_adjustment",
                        changes_made,
                        engagement_score > 0.7,
                    )
                    applied_personalization_history = True

                if engagement_score > 0.8 and content_length > 800:
                    if preferences.format_preferences.formatting_style != "structured":
                        preferences.format_preferences.formatting_style = "structured"
                        applied_preferences = True

                        self._log_adaptation(
                            personalization_history,
                            "format_optimization",
                            {"formatting_style": "structured"},
                            True,
                        )
                        applied_personalization_history = True

        elif interaction_type == "chat_response":
            follow_up = bool(metadata.get("has_follow_up", False))
            if follow_up:
                current_freq = engagement_analytics.interaction_signals.follow_up_question_frequency or 0.0
                engagement_analytics.interaction_signals.follow_up_question_frequency = min(1.0, current_freq + 0.1)
                applied_engagement_analytics = True

            feedback = metadata.get("feedback")
            link_clicks = int(metadata.get("link_clicks", 0))
            source_exploration = int(metadata.get("source_exploration_clicks", 0))
            session_continuation = float(metadata.get("session_continuation_rate", 0.0))
            response_len = metadata.get("response_length", "medium")

            engagement_score = self._calc_engagement_score(feedback, link_clicks, source_exploration, session_continuation)

            current_detail = preferences.format_preferences.detail_level
            new_detail = current_detail

            if response_len in ["long", "detailed"]:
                if engagement_score > 0.7:
                    if current_detail == "concise":
                        new_detail = "balanced"
                    elif current_detail == "balanced":
                        new_detail = "comprehensive"
                elif engagement_score < 0.4:
                    if current_detail == "comprehensive":
                        new_detail = "balanced"
                    elif current_detail == "balanced":
                        new_detail = "concise"

            if new_detail != current_detail:
                preferences.format_preferences.detail_level = new_detail
                applied_preferences = True

                self._log_adaptation(
                    personalization_history,
                    "detail_level_adjustment",
                    {"old": current_detail, "new": new_detail},
                    engagement_score > 0.7,
                )
                applied_personalization_history = True

        elif interaction_type == "engagement_event":
            event_type = metadata.get("type")

            if event_type == "link_click":
                url = metadata.get("url", "") or metadata.get("data", {}).get("url", "")
                ctx = metadata.get("context", {})
                topic_name = ctx.get("topicName") if isinstance(ctx, dict) else None
                # Count by topic if provided
                if topic_name:
                    by_topic = engagement_analytics.link_clicks_by_topic or {}
                    by_topic[topic_name] = int(by_topic.get(topic_name, 0)) + 1
                    engagement_analytics.link_clicks_by_topic = by_topic

                    applied_engagement_analytics = True
                # Track recent link domains
                domain = None
                if url:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                    except Exception:
                        domain = None

                if domain:
                    recent = engagement_analytics.recent_link_domains or []
                    recent.append(domain)
                    engagement_analytics.recent_link_domains = recent[-50:]

                    applied_engagement_analytics = True

            elif event_type == "feedback":
                fb = (metadata.get("feedback") or "").strip().lower()
                if fb in ("up", "down"):
                    tf = engagement_analytics.feedback_signals.thumbs_feedback
                    tf[fb] = int(tf.get(fb, 0)) + 1
                    engagement_analytics.feedback_signals.thumbs_feedback = tf
                    applied_engagement_analytics = True

            elif event_type == "content_interaction":
                interaction = (metadata.get("interactionType") or "").strip()
                data = metadata.get("data", {}) or {}
                topic_name = data.get("topicName")

                # Handle implicit feedback from content interactions
                if interaction == "bookmark":
                    # Bookmarking shows strong interest - record analytics
                    finding_id = data.get("findingId")
                    if finding_id:
                        if topic_name:
                            by_topic = engagement_analytics.bookmarks_by_topic or {}
                            by_topic[topic_name] = int(by_topic.get(topic_name, 0)) + 1
                            engagement_analytics.bookmarks_by_topic = by_topic

                        recent = engagement_analytics.bookmarked_findings or []
                        recent.append(finding_id)
                        engagement_analytics.bookmarked_findings = recent[-50:]

                        applied_engagement_analytics = True

                elif interaction == "integrate_to_knowledge_graph":
                    # Integration indicates very strong utility; record analytics
                    finding_id = data.get("findingId")
                    if finding_id:
                        if topic_name:
                            by_topic = dict(engagement_analytics.integrations_by_topic or {})
                            by_topic[topic_name] = int(by_topic.get(topic_name, 0)) + 1
                            engagement_analytics.integrations_by_topic = by_topic

                        recent = engagement_analytics.integrated_findings or []
                        recent.append(finding_id)
                        engagement_analytics.integrated_findings = recent[-50:]

                        applied_engagement_analytics = True

                elif interaction == "expand":
                    if topic_name:
                        # Could boost research priority for this topic
                        # Placeholder for future weighting
                        pass

                elif interaction == "link_click":
                    # Link click routed through engagement tracker
                    url = data.get("url")
                    if topic_name:
                        by_topic = engagement_analytics.link_clicks_by_topic or {}
                        by_topic[topic_name] = int(by_topic.get(topic_name, 0)) + 1
                        engagement_analytics.link_clicks_by_topic = by_topic

                        applied_engagement_analytics = True

                    domain = None
                    if url:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(url).netloc
                        except Exception:
                            domain = None

                    if domain:
                        recent = engagement_analytics.recent_link_domains or []
                        recent.append(domain)
                        engagement_analytics.recent_link_domains = recent[-50:]

                        applied_engagement_analytics = True

                elif interaction == "mark_read":
                    trigger = data.get("trigger", "unknown")
                    action = data.get("action", "unknown")
                    finding_id = data.get("findingId")
                    if finding_id:
                        if trigger == "topic_expansion" and action == "expansion_read":
                            # Expansion-based reading indicates interest in the topic but less deliberate than manual clicking
                            # Use moderate positive engagement score (0.6)
                            engagement_score = 0.6

                            # Extract any source types or content characteristics
                            # Note: In a real implementation, you'd fetch the finding details to get source types
                            # For now, we'll focus on topic-level learning

                            # Log this as a moderate positive interaction
                            self._log_adaptation(
                                personalization_history,
                                "expansion_based_read",
                                {"topic": topic_name, "finding_id": finding_id, "engagement_score": engagement_score},
                                True
                            )
                            applied_personalization_history = True
                        elif trigger == "manual_click" and action == "manual_read":
                            # Manual read button clicking indicates deliberate positive engagement
                            # Use strong positive engagement score (0.8)
                            engagement_score = 0.8

                            # This is a deliberate action showing content was valuable
                            # In a real implementation, you'd fetch finding details to learn source preferences

                            # Log this as a strong positive interaction
                            self._log_adaptation(
                                personalization_history,
                                "manual_read_action",
                                {"finding_id": finding_id, "engagement_score": engagement_score},
                                True
                            )
                            applied_personalization_history = True
                        else:
                            # Generic read action
                            pass

        if applied_preferences or applied_engagement_analytics or applied_personalization_history:
            if applied_preferences:
                await self._save_preferences(profile, preferences)
            if applied_engagement_analytics:
                await self._save_engagement_analytics(profile, engagement_analytics)
            if applied_personalization_history:
                await self._save_personalization_history(profile, personalization_history)

            await session.commit()

    async def apply_override(
        self,
        session: AsyncSession,
        profile: UserProfile,
        preference_type: str,
        override_value: Any,
        disable_learning: bool = False,
    ) -> None:
        preferences = self._load_preferences(profile)
        engagement_analytics = self._load_engagement_analytics(profile)
        personalization_history = self._load_personalization_history(profile)

        applied = False

        if preference_type.startswith("source_preference_"):
            source_type_index = preference_type.replace("source_preference_", "", 1)
            source_type = dict(preferences.content_preferences.source_types or {})
            if source_type_index in source_type or isinstance(override_value, (int, float)):
                source_type[source_type_index] = float(override_value)
                preferences.content_preferences.source_types = source_type
                applied = True

        elif preference_type == "detail_level":
            preferences.format_preferences.detail_level = override_value
            applied = True

        elif preference_type == "response_length":
            preferences.format_preferences.response_length = override_value
            applied = True

        if applied and disable_learning:
            if engagement_analytics.user_overrides is None:
                engagement_analytics.user_overrides = {}
            engagement_analytics.user_overrides[preference_type] = {
                "value": override_value,
                "learning_disabled": True,
                "timestamp": time.time(),
            }
            await self._save_engagement_analytics(profile, engagement_analytics)

        if applied:
            self._log_adaptation(
                personalization_history,
                "user_override",
                {"type": preference_type, "value": override_value, "learning_disabled": disable_learning},
                True,
            )
            await self._save_personalization_history(profile, personalization_history)
            await self._save_preferences(profile, preferences)

            await session.commit()

    def _ensure_profile(
        self,
        session: AsyncSession,
        user: User,
    ) -> UserProfile:
        if user.profile is not None:
            return user.profile

        profile = UserProfile(user_id=user.id, meta_data={})
        session.add(profile)

        return profile

    def _load_preferences(self, profile: UserProfile) -> PreferencesConfig:
        return PreferencesConfig.model_validate(profile.preferences or {})

    async def _save_preferences(self, profile: UserProfile, preferences: PreferencesConfig) -> None:
        profile.preferences = preferences.model_dump()

    def _load_engagement_analytics(self, profile: UserProfile) -> EngagementAnalytics:
        return EngagementAnalytics.model_validate(profile.engagement_analytics or {})

    async def _save_engagement_analytics(self, profile: UserProfile, engagement_analytics: EngagementAnalytics) -> None:
        profile.engagement_analytics = engagement_analytics.model_dump()

    def _load_personalization_history(self, profile: UserProfile) -> PersonalizationHistory:
        return PersonalizationHistory.model_validate(profile.personalization_history or {})

    async def _save_personalization_history(self, profile: UserProfile, personalization_history: PersonalizationHistory) -> None:
        profile.personalization_history = personalization_history.model_dump()

    def _log_adaptation(
        self,
        history: PersonalizationHistory,
        adaptation_type: str,
        changes: Dict[str, Any],
        positive: bool,
    ) -> None:
        log_entry = AdaptationLogEntry(
            timestamp=time.time(),
            adaptation_type=adaptation_type,
            change_made=f"Automatically adjusted {adaptation_type} based on usage patterns",
            changes_detail=changes,
            user_feedback=None,
            effectiveness_score=0.8 if positive else 0.3,
        )

        history.adaptation_log.append(log_entry)

        if len(history.adaptation_log) > 50:
            history.adaptation_log = history.adaptation_log[-50:]

    def _calc_engagement_score(
        self,
        feedback: Optional[str] = None,
        link_clicks: int = 0,
        source_exploration: int = 0,
        session_continuation: float = 0.0,
    ) -> float:
        """
        Calculate engagement score using new metrics (replacing reading time).

        Returns:
            Float between 0.0 and 1.0 representing engagement level
        """
        score = 0.0

        # Thumbs feedback (30% weight)
        if feedback == "up":
            score += 0.3
        elif feedback == "down":
            score -= 0.1 # Slight negative weight

        # Session continuation (25% weight)
        score += session_continuation * 0.25

        # Link clicks (20% weight) - normalized
        normalized_clicks = min(1.0, link_clicks / 3.0) # 3+ clicks = max score
        score += normalized_clicks * 0.2

        # Source exploration (15% weight)
        if source_exploration > 0:
            score += 0.15

        return max(0.0, min(1.0, score))
