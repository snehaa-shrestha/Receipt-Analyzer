from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ReceiptItem(BaseModel):
    description: str
    amount: float
    quantity: Optional[float] = 1.0
    category: Optional[str] = "Uncategorized"

class ReceiptSchema(BaseModel):
    user_id: str
    image_url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    merchant_name: Optional[str] = None
    total_amount: Optional[float] = None
    date_extracted: Optional[datetime] = None
    items: List[ReceiptItem] = []
    raw_text: Optional[str] = None
    ocr_confidence: Optional[float] = None

class ExpenseSchema(BaseModel):
    user_id: Optional[str] = None
    amount: float
    category: str
    date: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None
    receipt_id: Optional[str] = None
    is_manual: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "60d5ec...",
                "amount": 50.0,
                "category": "Food",
                "date": "2023-10-27T10:00:00",
                "description": "Lunch at Cafe",
                "is_manual": True
            }
        }
