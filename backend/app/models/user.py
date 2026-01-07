from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class UserSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(...)
    full_name: Optional[str] = None
    monthly_budget: Optional[float] = 2000.0
    currency: Optional[str] = "USD"
    disabled: Optional[bool] = False
    password: str = Field(...)
    points: int = 0
    streak_count: int = 0
    last_active_date: Optional[datetime] = None
    completed_quests: List[int] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "jdoe@example.com",
                "password": "hashed_secret_password",
                "points": 100,
                "streak_count": 5
            }
        }

class UserLoginSchema(BaseModel):
    username: str = Field(...)
    password: str = Field(...)
