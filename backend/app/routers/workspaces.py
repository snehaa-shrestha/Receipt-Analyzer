from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional
from bson import ObjectId
from app.utils.security import get_current_user
from app.database import get_database
from app.models.workspace import WorkspaceSchema, WorkspaceMember
from datetime import datetime

router = APIRouter()

@router.post("/")
async def create_workspace(workspace: WorkspaceSchema, current_user: dict = Depends(get_current_user)):
    db = get_database()
    
    # Add creator as admin
    workspace.members = [WorkspaceMember(user_id=current_user["user_id"], role="admin")]
    workspace.created_by = current_user["user_id"]
    workspace.created_at = datetime.utcnow()
    
    workspace_dict = workspace.model_dump()
    result = await db.workspaces.insert_one(workspace_dict)
    
    return {"message": "Workspace created successfully", "workspace_id": str(result.inserted_id)}

@router.get("/")
async def get_my_workspaces(current_user: dict = Depends(get_current_user)):
    db = get_database()
    user_id = current_user["user_id"]
    
    # Return all workspaces where user is a member
    cursor = db.workspaces.find({"members.user_id": user_id})
    workspaces = await cursor.to_list(length=100)
    
    # Collect all unique user IDs across all workspaces
    all_user_ids = set()
    for w in workspaces:
        for m in w.get("members", []):
            all_user_ids.add(m.get("user_id"))
            
    # Fetch usernames for these IDs
    from bson import ObjectId
    user_map = {}
    if all_user_ids:
        # Some IDs might be objectids, some might be strings based on data history.
        obj_ids = []
        str_ids = []
        for uid in all_user_ids:
            try:
                obj_ids.append(ObjectId(uid))
            except:
                pass
            str_ids.append(uid)
            
        users_cursor = db.users.find({"$or": [{"_id": {"$in": obj_ids}}, {"_id": {"$in": str_ids}}]})
        users = await users_cursor.to_list(length=len(all_user_ids))
        for u in users:
            user_map[str(u["_id"])] = u.get("username", "Unknown User")
            
    for w in workspaces:
        w["_id"] = str(w["_id"])
        for m in w.get("members", []):
            m["username"] = user_map.get(str(m.get("user_id")), m.get("user_id"))
        
    return workspaces

@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    try:
        w_id = ObjectId(workspace_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")
        
    workspace = await db.workspaces.find_one({"_id": w_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Check if user is member
    is_member = any(m["user_id"] == current_user["user_id"] for m in workspace["members"])
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
        
    # Fetch user data for members
    member_ids = [m["user_id"] for m in workspace.get("members", [])]
    if member_ids:
        from bson import ObjectId
        obj_ids = []
        str_ids = []
        for uid in member_ids:
            try:
                obj_ids.append(ObjectId(uid))
            except:
                pass
            str_ids.append(uid)
            
        users_cursor = db.users.find({"$or": [{"_id": {"$in": obj_ids}}, {"_id": {"$in": str_ids}}]})
        users = await users_cursor.to_list(length=len(member_ids))
        user_map = {str(u["_id"]): u.get("username", "Unknown User") for u in users}
        
        for m in workspace.get("members", []):
            m["username"] = user_map.get(str(m["user_id"]), m["user_id"])
            
    workspace["_id"] = str(workspace["_id"])
    return workspace

@router.post("/{workspace_id}/invite")
async def invite_user(
    workspace_id: str, 
    user_to_invite: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    try:
        w_id = ObjectId(workspace_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")
        
    workspace = await db.workspaces.find_one({"_id": w_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Verify inviter is admin
    user_role = next((m["role"] for m in workspace["members"] if str(m.get("user_id", "")) == str(current_user["user_id"])), None)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can invite members")
        
    # Check if already a member
    if any(m["user_id"] == user_to_invite for m in workspace["members"]):
        raise HTTPException(status_code=400, detail="User is already a member")
        
    # Add member
    new_member = {"user_id": user_to_invite, "role": "member"}
    await db.workspaces.update_one(
        {"_id": w_id},
        {"$push": {"members": new_member}}
    )
    
    return {"message": "User invited successfully"}

@router.put("/{workspace_id}/budget")
async def update_workspace_budget(
    workspace_id: str, 
    budget: float = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    try:
        w_id = ObjectId(workspace_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")
        
    workspace = await db.workspaces.find_one({"_id": w_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Verify updater is admin
    user_role = next((m.get("role") for m in workspace.get("members", []) if str(m.get("user_id", "")) == str(current_user["user_id"])), None)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update budget")
        
    await db.workspaces.update_one(
        {"_id": w_id},
        {"$set": {"budget": budget}}
    )
    
    return {"message": "Budget updated successfully", "budget": budget}

@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str, 
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    try:
        w_id = ObjectId(workspace_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")
        
    workspace = await db.workspaces.find_one({"_id": w_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    # Verify deleter is admin
    user_role = next((m.get("role") for m in workspace.get("members", []) if str(m.get("user_id", "")) == str(current_user["user_id"])), None)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admins can delete the workspace")
        
    # 1. Delete all expenses associated with this workspace
    await db.expenses.delete_many({"workspace_id": workspace_id})
    
    # 2. Delete all receipts associated with this workspace
    await db.receipts.delete_many({"workspace_id": workspace_id})
    
    # 3. Delete all chat messages associated with this workspace
    await db.messages.delete_many({"room_id": workspace_id})
    
    # 4. Delete the workspace itself
    await db.workspaces.delete_one({"_id": w_id})
    
    return {"message": "Workspace and all associated records deleted successfully"}
