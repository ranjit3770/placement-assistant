from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.security import Principal

@dataclass(frozen=True)
class ToolContext:
    principal: Principal
    request_id: str
    db_session: Any = None  # Could hold a session if needed, though tools usually get their own or rely on services
