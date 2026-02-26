from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class WorkspaceMember(BaseModel):
    user_id: str
    role: str = "member" # "admin" or "member"

class WorkspaceSchema(BaseModel):
    name: str
    type: str = "group" # "group" or "individual"
    members: List[WorkspaceMember] = []
    budget: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

class ConnectionSchema(BaseModel):
    user_id: str
    friend_id: str
    status: str = "pending" # "pending" or "accepted"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MessageSchema(BaseModel):
    workspace_id: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
