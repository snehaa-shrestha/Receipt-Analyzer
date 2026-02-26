from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from app.utils.security import get_current_user
from app.database import get_database
from app.models.workspace import ConnectionSchema
from datetime import datetime

router = APIRouter()

@router.get("/search")
async def search_users(
    query: str = Query(..., min_length=2),
    current_user: dict = Depends(get_current_user)
):
    """Search for users by username or email"""
    db = get_database()
    # Find active non-deleted users matching query
    search_regex = {"$regex": query, "$options": "i"}
    users_cursor = db.users.find({
        "$and": [
            {"_id": {"$ne": ObjectId(current_user["user_id"])}},
            {"$or": [{"username": search_regex}, {"email": search_regex}]}
        ]
    }, {"password": 0}).limit(20)
    
    users = await users_cursor.to_list(length=20)
    
    # Check connection status for each user found
    results = []
    for u in users:
        conn = await db.connections.find_one({
            "$or": [
                {"user_id": current_user["user_id"], "friend_id": str(u["_id"])},
                {"user_id": str(u["_id"]), "friend_id": current_user["user_id"]}
            ]
        })
        status = conn["status"] if conn else "none"
        is_sender = conn["user_id"] == current_user["user_id"] if conn else False
        
        results.append({
            "id": str(u["_id"]),
            "username": u.get("username"),
            "email": u.get("email"),
            "connection_status": status,
            "is_sender": is_sender
        })
        
    return results

@router.post("/connect/{friend_id}")
async def send_connection_request(friend_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    if friend_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot connect with yourself")
        
    # Check if friend exists
    friend = await db.users.find_one({"_id": ObjectId(friend_id)})
    if not friend:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Check existing connection
    existing = await db.connections.find_one({
        "$or": [
            {"user_id": current_user["user_id"], "friend_id": friend_id},
            {"user_id": friend_id, "friend_id": current_user["user_id"]}
        ]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Connection already {existing['status']}")
        
    new_conn = {
        "user_id": current_user["user_id"],
        "friend_id": friend_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    await db.connections.insert_one(new_conn)
    return {"message": "Connection request sent"}

@router.put("/connect/{friend_id}/accept")
async def accept_connection(friend_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    # The request must have been sent BY the friend TO the current user
    result = await db.connections.update_one(
        {"user_id": friend_id, "friend_id": current_user["user_id"], "status": "pending"},
        {"$set": {"status": "accepted"}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Pending request not found")
    return {"message": "Connection accepted"}

@router.get("/connections")
async def get_connections(current_user: dict = Depends(get_current_user)):
    db = get_database()
    user_id = current_user["user_id"]
    
    # Fetch where status is accepted and user is either user_id or friend_id
    conns = await db.connections.find({
        "status": "accepted",
        "$or": [{"user_id": user_id}, {"friend_id": user_id}]
    }).to_list(length=1000)
    
    # We need friend details
    friend_ids = [ObjectId(c["friend_id"] if c["user_id"] == user_id else c["user_id"]) for c in conns]
    
    friends = await db.users.find({"_id": {"$in": friend_ids}}, {"password": 0}).to_list(length=1000)
    
    return [{"id": str(f["_id"]), "username": f.get("username"), "email": f.get("email")} for f in friends]
