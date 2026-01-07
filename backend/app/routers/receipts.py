from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from typing import List, Optional
from app.utils.security import verify_password, ALGORITHM, SECRET_KEY
from app.database import get_database
from app.models.receipt import ReceiptSchema
from app.services.ocr_service import extract_text, parse_receipt
from app.services.ml_service import classify_text
from datetime import datetime
import shutil
import os
import uuid
from app.utils.security import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...), 
    manual_date: Optional[str] = Query(None),
    manual_category: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    from app.services.game_service import update_streak
    await update_streak(current_user["user_id"])
    
    try:
        # Save file
        file_ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Read file for OCR
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        # Run OCR
        text = extract_text(file_bytes)
        parsed_data = parse_receipt(text)
        
        # Enrich items with categories (Prioritize Manual Category if set)
        enriched_items = []
        for item in parsed_data.get("items", []):
            category = manual_category if manual_category else classify_text(item["description"])
            enriched_items.append({
                "description": item["description"],
                "amount": item["amount"],
                "quantity": 1.0,
                "category": category
            })
        
        # Determine date - Prioritize OCR extraction, fallback to manual, then upload date
        final_date = parsed_data.get("date_extracted")
        
        # If manual date provided and OCR failed, use manual
        if not final_date and manual_date:
            try:
                final_date = datetime.fromisoformat(manual_date.replace('Z', '+00:00'))
            except:
                pass
        
        # Final fallback: use upload date
        if not final_date:
            final_date = datetime.utcnow()

        # Create Receipt Object
        receipt_data = {
            "user_id": current_user["user_id"],
            "image_url": filepath, # In prod, return a static URL
            "uploaded_at": datetime.utcnow(),
            "merchant_name": parsed_data["merchant_name"],
            "total_amount": parsed_data["total_amount"],
            "date_extracted": final_date,
            "raw_text": text,
            "items": enriched_items
        }
        
        db = get_database()
        new_receipt = await db.receipts.insert_one(receipt_data)
        receipt_id = str(new_receipt.inserted_id)

        # 2. Insert individual items as Expenses for Analytics
        expense_docs = []
        for item in enriched_items:
            expense_docs.append({
                "user_id": current_user["user_id"],
                "description": item["description"],
                "amount": item["amount"],
                "category": item["category"],
                "date": final_date,
                "receipt_id": receipt_id,
                "created_at": datetime.utcnow()
            })
            
        if expense_docs:
            await db.expenses.insert_many(expense_docs)
        elif receipt_data["total_amount"] > 0:
            # Fallback: If no items parsed but we have a total, create a single expense
            merchant_name = parsed_data.get("merchant_name", "Receipt Total")
            cat = manual_category if manual_category else classify_text(merchant_name)
            
            await db.expenses.insert_one({
                "user_id": current_user["user_id"],
                "description": merchant_name,
                "amount": receipt_data["total_amount"],
                "category": cat,
                "date": final_date,
                "receipt_id": receipt_id,
                "created_at": datetime.utcnow()
            })
        
        # Update parsed_data with the final decided values so frontend sees them
        parsed_data["date_extracted"] = final_date
        parsed_data["merchant_name"] = parsed_data.get("merchant_name") # Keep as is
        
        return {
            "message": "Receipt uploaded and processed", 
            "receipt_id": str(new_receipt.inserted_id),
            "parsed_data": parsed_data
        }
        
    except Exception as e:
        print(f"UPLOAD FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_receipts(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    amount: int = 10,
    search: Optional[str] = None
):
    db = get_database()
    query = {"user_id": current_user["user_id"]}
    
    if search:
        # Text search on merchant or raw text
        query["$or"] = [
            {"merchant_name": {"$regex": search, "$options": "i"}},
            {"raw_text": {"$regex": search, "$options": "i"}}
        ]
        
    cursor = db.receipts.find(query).skip(skip).limit(amount).sort("uploaded_at", -1)
    receipts = await cursor.to_list(length=amount)
    
    # Convert ObjectId to string
    for r in receipts:
        r["_id"] = str(r["_id"])
        
    return receipts

@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    from bson import ObjectId
    
    try:
        r_oid = ObjectId(receipt_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid receipt ID")
        
    # Find receipt
    receipt = await db.receipts.find_one({
        "_id": r_oid, 
        "user_id": current_user["user_id"]
    })
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    # 1. Delete associated Image File
    try:
        if receipt.get("image_url") and os.path.exists(receipt["image_url"]):
            os.remove(receipt["image_url"])
    except Exception as e:
        print(f"Error deleting file: {e}")
        
    # 2. Delete associated Expenses (Cascade)
    await db.expenses.delete_many({"receipt_id": receipt_id})
    
    # 3. Delete Receipt
    await db.receipts.delete_one({"_id": r_oid})
    
    return {"message": "Receipt and associated data deleted successfully"}
