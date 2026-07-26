from fastapi import APIRouter, Depends
from app.database import get_database
from app.utils.security import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter()

from app.services.game_service import check_and_update_quests, get_display_streak

@router.get("/progress")
async def get_progress(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    db = get_database()
    
    active_quests, points = await check_and_update_quests(user_id)
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    streak = get_display_streak(user)
    
    level = 0
    next_level_points = 50
    current_tier_xp = 50
    
    total_xp_needed = 50
    current_level_base_xp = 0
    while points >= total_xp_needed:
        level += 1
        current_level_base_xp = total_xp_needed
        current_tier_xp += 50
        total_xp_needed += current_tier_xp

    return {
        "points": points,
        "streak_count": streak,
        "level": level,
        "current_level_base_xp": current_level_base_xp,
        "next_level_points": total_xp_needed,
        "active_quests": active_quests
    }

