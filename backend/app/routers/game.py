from fastapi import APIRouter, Depends
from app.database import get_database
from app.utils.security import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter()

from app.services.game_service import check_and_update_quests

@router.get("/progress")
async def get_progress(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    db = get_database()
    
    # Calculate quests and update DB if needed
    active_quests, points = await check_and_update_quests(user_id)
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    streak = user.get("streak_count", 0)
    level = (points // 100) + 1

    return {
        "points": points,
        "streak_count": streak,
        "level": level,
        "next_level_points": level * 100,
        "active_quests": active_quests
    }

