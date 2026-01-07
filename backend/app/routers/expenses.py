from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import List, Optional
from app.utils.security import ALGORITHM, SECRET_KEY, get_current_user
from app.database import get_database
from app.models.receipt import ExpenseSchema
from app.services.ml_service import predict_next_month_expenses, categorize_expense_rule_based
from datetime import datetime

router = APIRouter()

@router.post("/")
async def create_expense(expense: ExpenseSchema, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    expense.user_id = user_id
    
    if not expense.category or expense.category == "Uncategorized":
        expense.category = categorize_expense_rule_based(expense.description or "", expense.amount)
        
    db = get_database()
    new_expense = await db.expenses.insert_one(expense.model_dump())
    return {"message": "Expense added", "id": str(new_expense.inserted_id)}

@router.get("/")
async def get_expenses(current_user: dict = Depends(get_current_user)):
    """
    Returns ALL transactions (Merged Receipts + Manual Expenses)
    """
    user_id = current_user["user_id"]
    db = get_database()
    
    # 1. Fetch Receipts
    receipts = await db.receipts.find({"user_id": user_id}).sort("date_extracted", -1).to_list(length=100)
    
    # 2. Fetch Manual Expenses
    manual_expenses = await db.expenses.find({"user_id": user_id, "receipt_id": None}).sort("date", -1).to_list(length=100)
    
    combined = []
    
    for r in receipts:
        combined.append({
            "_id": str(r["_id"]), # Match frontend expectation
            "type": "receipt",
            "description": r.get("merchant_name", "Unknown Merchant"),
            "amount": r.get("total_amount", 0.0),
            "date": r.get("date_extracted") or r.get("uploaded_at"),
            "category": "Receipt", # Receipts might not have a single category, defaulting
            "receipt_id": str(r["_id"])
        })
        
    for e in manual_expenses:
        combined.append({
            "_id": str(e["_id"]),
            "type": "expense",
            "description": e.get("description", "Unknown Expense"),
            "amount": e.get("amount", 0.0),
            "date": e.get("date"),
            "category": e.get("category", "Uncategorized"),
            "receipt_id": None
        })
        
    # Sort by date desc
    combined.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    return combined

@router.get("/recent-transactions")
async def get_recent_transactions(current_user: dict = Depends(get_current_user)):
    # Reuse get_expenses logic efficiently? Or just keep separate for limit=10 optimization
    # For now, duplicate logic but smaller limit to be safe
    user_id = current_user["user_id"]
    db = get_database()
    
    receipts = await db.receipts.find({"user_id": user_id}).sort("date_extracted", -1).limit(10).to_list(length=10)
    manual_expenses = await db.expenses.find({"user_id": user_id, "receipt_id": None}).sort("date", -1).limit(10).to_list(length=10)
    
    combined = []
    for r in receipts:
        combined.append({
            "_id": str(r["_id"]),
            "type": "receipt",
            "description": r.get("merchant_name", "Unknown Merchant"),
            "amount": r.get("total_amount", 0.0),
            "date": r.get("date_extracted") or r.get("uploaded_at"),
            "category": "Receipt",
            "receipt_id": str(r["_id"])
        })
    for e in manual_expenses:
        combined.append({
            "_id": str(e["_id"]),
            "type": "expense",
            "description": e.get("description", "Unknown Expense"),
            "amount": e.get("amount", 0.0),
            "date": e.get("date"),
            "category": e.get("category", "Uncategorized"),
            "receipt_id": None
        })
    combined.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    return combined[:10]

@router.get("/summary")
async def get_expense_summary(
    current_user: dict = Depends(get_current_user),
    period: str = Query("all", enum=["month", "year", "all"]),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    db = get_database()
    user_id = current_user["user_id"]
    
    # Prepare Date Query
    match_query = {}
    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month

    start_date = None
    end_date = None

    if period == "month":
        start_date = datetime(target_year, target_month, 1)
        if target_month == 12: year_end, month_end = target_year + 1, 1
        else: year_end, month_end = target_year, target_month + 1
        end_date = datetime(year_end, month_end, 1)
        
    elif period == "year":
        start_date = datetime(target_year, 1, 1)
        end_date = datetime(target_year + 1, 1, 1)

    # 1. Aggregate Manual Expenses
    exp_match = {"user_id": user_id, "receipt_id": None}
    if start_date: exp_match["date"] = {"$gte": start_date, "$lt": end_date}
    
    exp_pipeline = [
        {"$match": exp_match},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
    ]
    exp_result = await db.expenses.aggregate(exp_pipeline).to_list(None)
    
    # 2. Aggregate Receipts (Counts as "Shopping" or "Receipt")
    # Note: Receipts table might not have 'category', usually "Shopping" or we classify merchant
    rcpt_match = {"user_id": user_id}
    if start_date: rcpt_match["date_extracted"] = {"$gte": start_date, "$lt": end_date} # Use date_extracted
    
    rcpt_pipeline = [
        {"$match": rcpt_match},
        {"$group": {"_id": "Receipts", "total": {"$sum": "$total_amount"}}}
    ]
    rcpt_result = await db.receipts.aggregate(rcpt_pipeline).to_list(None)
    
    # Merge Results
    summary = {}
    for r in exp_result:
        summary[r["_id"]] = summary.get(r["_id"], 0) + r["total"]
        
    for r in rcpt_result:
        # You might want to distribute this if you have real cats, but for now bucket as 'Shopping' or 'Receipts'
        cat = "Shopping" 
        summary[cat] = summary.get(cat, 0) + r["total"]
        
    # Format for frontend
    final_result = [{"_id": k, "total": v} for k, v in summary.items()]
    return final_result

@router.get("/forecast")
async def get_forecast(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    prediction = await predict_next_month_expenses(user_id)
    return prediction

@router.get("/export")
async def export_expenses(current_user: dict = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse
    import io
    import csv

    user_id = current_user["user_id"]
    db = get_database()
    
    # Fetch all expenses
    expenses = await db.expenses.find({"user_id": user_id}).sort("date", -1).to_list(length=10000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Date", "Merchant/Description", "Category", "Amount", "Source"])
    
    # Rows
    for ex in expenses:
        source = "Receipt Scanner" if ex.get("receipt_id") else "Manual/Digital"
        writer.writerow([
            ex.get("date", "").strftime("%Y-%m-%d") if isinstance(ex.get("date"), datetime) else ex.get("date"),
            ex.get("description", ""),
            ex.get("category", ""),
            ex.get("amount", 0),
            source
        ])
        
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=expenses_report.csv"
    response.headers["Content-Disposition"] = "attachment; filename=expenses_report.csv"
    return response

@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    from bson import ObjectId
    
    try:
        oid = ObjectId(expense_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid expense ID")
        
    result = await db.expenses.delete_one({"_id": oid, "user_id": current_user["user_id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    return {"message": "Expense deleted"}
