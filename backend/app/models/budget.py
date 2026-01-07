from pydantic import BaseModel, Field
from datetime import datetime

class BudgetSchema(BaseModel):
    user_id: str
    category: str
    limit: float
    month: int
    year: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "60d5ec...",
                "category": "Food",
                "limit": 500.0,
                "month": 10,
                "year": 2023
            }
        }
