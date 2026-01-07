from fastapi import APIRouter, Depends, HTTPException, Body
from app.database import get_database
from app.models.user import UserSchema
from app.utils.security import get_current_user
from pydantic import BaseModel

from bson import ObjectId

router = APIRouter()

class UserUpdate(BaseModel):
    full_name: str = None
    monthly_budget: float = None
    currency: str = None

@router.get("/me")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    # current_user from auth is just the decoded token dict usually, 
    # but in auth.py get_current_user returns a dict {"user_id": ..., "username": ...}
    # We need to fetch full details from DB
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(current_user["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return user data (excluding password)
    user["_id"] = str(user["_id"])
    user.pop("hashed_password", None)
    return user

@router.put("/me")
async def update_user_profile(
    update_data: UserUpdate, 
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    
    if not update_dict:
        return {"message": "No changes provided"}
        
    await db.users.update_one(
        {"_id": ObjectId(current_user["user_id"])},
        {"$set": update_dict}
    )
    
    return {"message": "Profile updated successfully"}
