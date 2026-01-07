from fastapi import APIRouter, Depends, HTTPException
from app.database import get_database
from app.utils.security import get_current_user
from app.models.budget import BudgetSchema
from datetime import datetime

router = APIRouter()

@router.post("/")
async def create_budget(budget: BudgetSchema, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    budget.user_id = user_id
    db = get_database()
    
    # Check if budget exists for this month/category
    existing = await db.budgets.find_one({
        "user_id": user_id, 
        "category": budget.category,
        "month": budget.month,
        "year": budget.year
    })
    
    if existing:
        await db.budgets.update_one({"_id": existing["_id"]}, {"$set": {"limit": budget.limit}})
        return {"message": "Budget updated"}
        
    await db.budgets.insert_one(budget.model_dump())
    return {"message": "Budget set"}

@router.get("/status")
async def get_budget_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    db = get_database()
    now = datetime.utcnow()
    current_month = now.month
    current_year = now.year
    
    # Get all budgets for current month
    budgets = await db.budgets.find({
        "user_id": user_id,
        "month": current_month,
        "year": current_year
    }).to_list(length=None)
    
    status = []
    
    for b in budgets:
        # Calculate spent for this category
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "category": b["category"],
                    "date": {
                        "$gte": datetime(current_year, current_month, 1),
                        "$lt": datetime(current_year, current_month + 1, 1) if current_month < 12 else datetime(current_year + 1, 1, 1)
                    }
                }
            },
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        result = await db.expenses.aggregate(pipeline).to_list(length=1)
        spent = result[0]["total"] if result else 0.0
        
        status.append({
            "category": b["category"],
            "limit": b["limit"],
            "spent": spent,
            "remaining": b["limit"] - spent,
            "alert": spent > b["limit"]
        })
        
    return status
