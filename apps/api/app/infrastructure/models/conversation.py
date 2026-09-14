from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, JSON

from app.infrastructure.database import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=func.gen_random_uuid())
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=func.gen_random_uuid())
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"), index=True
    )
    sequence_number: Mapped[int]
    role: Mapped[str] = mapped_column(String(50))
    content: Mapped[str | None]
    tool_name: Mapped[str | None] = mapped_column(String(100))
    tool_call_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message_metadata: Mapped[dict | None] = mapped_column(JSON)
    
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_number", name="uq_session_sequence"),
    )
