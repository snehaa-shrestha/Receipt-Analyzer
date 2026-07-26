from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from typing import Any, List, Optional
from pydantic import BaseModel
from app.utils.security import verify_password, ALGORITHM, SECRET_KEY
from app.database import get_database
from app.models.receipt import ReceiptSchema
from app.services.ocr_service import extract_text
from app.services.game_service import update_monthly_streak

from datetime import datetime
import shutil
import os
import uuid
from app.utils.security import get_current_user
from bson import ObjectId

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class ConfirmReceiptRequest(BaseModel):
    filename: str
    workspace_id: Optional[str] = None
    merchant_name: str
    total_amount: float
    date_extracted: str
    category: str
    items: List[dict]

@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...)
):
    try:
        file_ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        parsed_data = extract_text(file_bytes)
        
        return {
            "message": "Receipt analyzed. Please review.", 
            "parsed_data": parsed_data,
            "filename": filename
        }
    except Exception as e:
        print(f"UPLOAD FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
async def confirm_receipt(
    request: ConfirmReceiptRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        filepath = os.path.join(UPLOAD_DIR, request.filename)
        
        try:
            final_date = datetime.fromisoformat(request.date_extracted.replace('Z', '+00:00'))
        except:
            final_date = datetime.utcnow()
        
        receipt_data = {
            "user_id": current_user["user_id"],
            "workspace_id": request.workspace_id,
            "image_url": filepath,
            "uploaded_at": datetime.utcnow(),
            "merchant_name": request.merchant_name,
            "total_amount": request.total_amount,
            "date_extracted": final_date,
            "category": request.category,
            "items": request.items
        }
        
        db = get_database()
        new_receipt = await db.receipts.insert_one(receipt_data)
        receipt_id = str(new_receipt.inserted_id)
 
        expense_docs = []
        for item in request.items:
            # Handle both 'price' and 'amount' depending on what frontend sends
            amt = item.get("amount", item.get("price", 0))
            if amt is None or amt == "": amt = 0
            
            expense_docs.append({
                "user_id": current_user["user_id"],
                "workspace_id": request.workspace_id,
                "description": item.get("description", item.get("item_name", "Unknown Item")),
                "amount": float(amt),
                "category": item.get("category", request.category),
                "date": final_date,
                "receipt_id": receipt_id,
                "created_at": datetime.utcnow()
            })
            
        if expense_docs:
            await db.expenses.insert_many(expense_docs)
        elif request.total_amount > 0:
            await db.expenses.insert_one({
                "user_id": current_user["user_id"],
                "workspace_id": request.workspace_id,
                "description": request.merchant_name,
                "amount": request.total_amount,
                "category": request.category,
                "date": final_date,
                "receipt_id": receipt_id,
                "created_at": datetime.utcnow()
            })
        
        await update_monthly_streak(current_user["user_id"])

        if request.workspace_id:
            from app.routers.chat import manager
            await manager.broadcast_event(request.workspace_id, "expense_update", {})

        return {
            "message": "Receipt confirmed and saved", 
            "receipt_id": receipt_id
        }
    except Exception as e:
        print(f"CONFIRM FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_receipts(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    amount: int = 10,
    search: Optional[str] = None,
    category: Optional[str] = None,
    workspace_id: Optional[str] = None
):
    db = get_database()
    
    if workspace_id:
        workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
        if not workspace or not any(m["user_id"] == current_user["user_id"] for m in workspace.get("members", [])):
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        query: dict[str, Any] = {"workspace_id": workspace_id}
    else:
        query: dict[str, Any] = {"user_id": current_user["user_id"], "$or": [{"workspace_id": None}, {"workspace_id": {"$exists": False}}]}
    
    if search:
        query["$or"] = [
            {"merchant_name": {"$regex": search, "$options": "i"}},
            {"raw_text": {"$regex": search, "$options": "i"}}
        ]
        
    if category and category.lower() != "all":
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}
        
    cursor = db.receipts.find(query).skip(skip).limit(amount).sort("uploaded_at", -1)
    receipts = await cursor.to_list(length=amount)
    
    for r in receipts:
        r["_id"] = str(r["_id"])
        
    return receipts

@router.get("/{receipt_id}")
async def get_receipt(
    receipt_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    try:
        r_oid = ObjectId(receipt_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid receipt ID")
        
    receipt = await db.receipts.find_one({"_id": r_oid})
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    # Check permissions (basic check, could be expanded for workspaces)
    if receipt.get("user_id") != current_user["user_id"]:
        # Allow if it's in a workspace they belong to
        if receipt.get("workspace_id"):
            workspace = await db.workspaces.find_one({"_id": ObjectId(receipt["workspace_id"])})
            if not workspace or not any(m["user_id"] == current_user["user_id"] for m in workspace.get("members", [])):
                raise HTTPException(status_code=403, detail="Not authorized")
        else:
            raise HTTPException(status_code=403, detail="Not authorized")
            
    receipt["_id"] = str(receipt["_id"])
    return receipt

@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    
    try:
        r_oid = ObjectId(receipt_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid receipt ID")
        
    receipt = await db.receipts.find_one({"_id": r_oid})
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    if receipt.get("workspace_id"):
        workspace = await db.workspaces.find_one({"_id": ObjectId(receipt["workspace_id"])})
        is_admin = False
        if workspace:
            is_admin = any(m["user_id"] == current_user["user_id"] and m["role"] == "admin" for m in workspace.get("members", []))
        if receipt["user_id"] != current_user["user_id"] and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to delete this receipt")
    elif receipt["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this receipt")
    
    try:
        if receipt.get("image_url") and os.path.exists(receipt["image_url"]):
            os.remove(receipt["image_url"])
    except Exception as e:
        print(f"Error deleting file: {e}")
        
    await db.expenses.delete_many({"receipt_id": receipt_id})
    
    await db.receipts.delete_one({"_id": r_oid})
    
    return {"message": "Receipt and associated data deleted successfully"}

class SplitDataRequest(BaseModel):
    people: list
    assignments: dict

@router.put("/{receipt_id}/split")
async def save_receipt_split(
    receipt_id: str,
    request: SplitDataRequest,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    try:
        r_oid = ObjectId(receipt_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid receipt ID")
        
    receipt = await db.receipts.find_one({"_id": r_oid})
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    if receipt.get("workspace_id"):
        workspace = await db.workspaces.find_one({"_id": ObjectId(receipt["workspace_id"])})
        is_admin = False
        if workspace:
            is_admin = any(m["user_id"] == current_user["user_id"] and m["role"] == "admin" for m in workspace.get("members", []))
        if receipt["user_id"] != current_user["user_id"] and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to edit this receipt")
    elif receipt["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this receipt")
        
    await db.receipts.update_one(
        {"_id": r_oid},
        {"$set": {
            "split_people": request.people,
            "split_assignments": request.assignments
        }}
    )
    
    return {"message": "Split data saved successfully"}
