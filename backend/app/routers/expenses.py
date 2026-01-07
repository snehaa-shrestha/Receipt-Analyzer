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
    # Filter out transactions with null or zero amounts
    combined = [tx for tx in combined if tx.get("amount") and tx.get("amount") > 0]
    return combined

@router.get("/recent-transactions")
async def get_recent_transactions(
    current_user: dict = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    user_id = current_user["user_id"]
    db = get_database()
    
    # Date Filtering
    match_query = {"user_id": user_id}
    receipt_match = {"user_id": user_id}
    
    if year and month:
        start_date = datetime(year, month, 1)
        if month == 12: year_end, month_end = year + 1, 1
        else: year_end, month_end = year, month + 1
        end_date = datetime(year_end, month_end, 1)
        
        match_query["date"] = {"$gte": start_date, "$lt": end_date}
        
        # For receipts, use date_extracted or uploaded_at
        # Note: receipts table stores date_extracted
        receipt_match["date_extracted"] = {"$gte": start_date, "$lt": end_date}
    
    # We only need to fetch from expenses table now since it contains everything
    # But for backward compatibility with existing frontend that expects 'type' distinct differentiation
    # Let's perform the query on expenses table primarily
    
    expenses = await db.expenses.find(match_query).sort("date", -1).limit(10).to_list(length=10)
    
    combined = []
    for e in expenses:
        combined.append({
            "_id": str(e["_id"]),
            "type": "expense" if not e.get("receipt_id") else "receipt",
            "description": e.get("description", "Unknown"),
            "amount": e.get("amount", 0.0),
            "date": e.get("date"),
            "category": e.get("category", "Uncategorized"),
            "receipt_id": e.get("receipt_id")
        })
        
    combined.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    
    # Filter out transactions with null or zero amounts
    combined = [tx for tx in combined if tx.get("amount") and tx.get("amount") > 0]
    
    return combined[:5]

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

    # Aggregate ALL Expenses (both manual and from receipts)
    # Note: Receipt items are already stored in expenses table with receipt_id set
    # So we don't need to query receipts table separately to avoid double-counting
    exp_match = {"user_id": user_id}
    if start_date: exp_match["date"] = {"$gte": start_date, "$lt": end_date}
    
    exp_pipeline = [
        {"$match": exp_match},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
    ]
    exp_result = await db.expenses.aggregate(exp_pipeline).to_list(None)
    
    # Build summary from expenses only (no double-counting)
    summary = {}
    for r in exp_result:
        category = r["_id"] or "Uncategorized"
        summary[category] = summary.get(category, 0) + r["total"]
        
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
