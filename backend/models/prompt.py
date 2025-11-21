from __future__ import annotations
import uuid
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False, default=list
    )

    updated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class PromptHistory(Base):
    __tablename__ = "prompt_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"),
    )

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False, default=list
    )

    updated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by_profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        primaryjoin="PromptHistory.updated_by_user_id==foreign(UserProfile.user_id)",
        viewonly=True,
        lazy="select",
    )

    @property
    def user(self) -> str:
        md = getattr(self.updated_by_profile, "meta_data", None) or {}
        return md.get("display_name") or "unknown"