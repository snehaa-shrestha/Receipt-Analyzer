from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import get_current_user
from app.services.ai_advisor import get_financial_advice

router = APIRouter()

@router.get("/advice")
async def get_advice(
    current_user: dict = Depends(get_current_user),
    year: int = None,
    month: int = None
):
    user_id = current_user["user_id"]
    advice = await get_financial_advice(user_id, year, month)
    return advice
