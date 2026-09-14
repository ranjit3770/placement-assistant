from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ToolContext
from app.infrastructure.models.conversation import ConversationSession, ConversationMessage
from app.agent.m8_authority import M8EligibilityRepository


class ConversationMemory:
    def __init__(self, db: AsyncSession, context: ToolContext):
        self.db = db
        self.context = context
        self.institution_id = context.principal.institution_id

    async def get_or_create_session(self, conversation_id: UUID) -> ConversationSession:
        student_id = await M8EligibilityRepository(self.db, self.context.principal).owned_student()
        stmt = select(ConversationSession).where(
            and_(
                ConversationSession.id == conversation_id,
                ConversationSession.institution_id == self.institution_id,
                ConversationSession.student_id == student_id,
            )
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            # If a session exists with this ID but different owner, inserting will fail due to PK constraint
            # Or we can explicitly check if it exists for someone else first to return a clear 403,
            # but letting PK violation handle forged IDs across tenants is also safe.
            # Let's explicitly check to avoid 500s.
            existing = await self.db.execute(select(ConversationSession.id).where(ConversationSession.id == conversation_id))
            if existing.scalar_one_or_none():
                raise PermissionError("Access to this conversation is denied.")
            
            session = ConversationSession(
                id=conversation_id,
                institution_id=self.institution_id,
                student_id=student_id
            )
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
        return session

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        metadata: dict | None = None
    ) -> ConversationMessage:
        # First ensure the session exists and belongs to the user
        session = await self.get_or_create_session(conversation_id)
        
        # Get next sequence number
        stmt = select(ConversationMessage.sequence_number).where(
            ConversationMessage.session_id == session.id
        ).order_by(ConversationMessage.sequence_number.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        last_seq = result.scalar_one_or_none() or 0
        next_seq = last_seq + 1

        message = ConversationMessage(
            session_id=session.id,
            sequence_number=next_seq,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            message_metadata=metadata
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message


    async def list_sessions(self) -> list[ConversationSession]:
        student_id = await M8EligibilityRepository(self.db, self.context.principal).owned_student()
        stmt = select(ConversationSession).where(
            and_(
                ConversationSession.institution_id == self.institution_id,
                ConversationSession.student_id == student_id,
            )
        ).order_by(ConversationSession.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_raw_messages(self, conversation_id: UUID) -> list[ConversationMessage]:
        session = await self.get_or_create_session(conversation_id)
        stmt = select(ConversationMessage).where(
            ConversationMessage.session_id == session.id
        ).order_by(ConversationMessage.sequence_number.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_messages(self, conversation_id: UUID) -> list[dict]:
        session = await self.get_or_create_session(conversation_id)
        
        stmt = select(ConversationMessage).where(
            ConversationMessage.session_id == session.id
        ).order_by(ConversationMessage.sequence_number.asc())
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Format for OpenAI API
        formatted = []
        for m in messages:
            msg = {"role": m.role}
            if m.content is not None:
                msg["content"] = m.content
            if m.tool_name is not None:
                msg["name"] = m.tool_name
            if m.tool_call_id is not None:
                msg["tool_call_id"] = m.tool_call_id
            if m.message_metadata and "tool_calls" in m.message_metadata:
                msg["tool_calls"] = m.message_metadata["tool_calls"]
            formatted.append(msg)
            
        return formatted
