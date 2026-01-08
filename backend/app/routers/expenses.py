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
async def get_expenses(
    current_user: dict = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """
    Returns transactions (Merged Receipts + Manual Expenses).
    If year/month provided, returns ALL matching records.
    If no filter, returns recent 100.
    """
    user_id = current_user["user_id"]
    db = get_database()
    
    # Date Filtering
    date_query = {}
    limit = 100 # default limit for recent
    
    if year:
        limit = 0 # no limit if filtering
        start_date = datetime(year, month if month else 1, 1)
        if month:
            if month == 12: end_date = datetime(year + 1, 1, 1)
            else: end_date = datetime(year, month + 1, 1)
        else:
            end_date = datetime(year + 1, 1, 1)
        date_query = {"$gte": start_date, "$lt": end_date}
    
    # 1. Fetch Receipts
    receipt_match = {"user_id": user_id}
    if date_query: receipt_match["date_extracted"] = date_query
    
    r_cursor = db.receipts.find(receipt_match).sort("date_extracted", -1)
    if limit > 0: r_cursor = r_cursor.limit(limit)
    receipts = await r_cursor.to_list(length=None) # length=None is safe here as mongo driver handles it, or pass 10000
    
    # 2. Fetch Manual Expenses
    expense_match = {"user_id": user_id, "receipt_id": None}
    if date_query: expense_match["date"] = date_query
    
    e_cursor = db.expenses.find(expense_match).sort("date", -1)
    if limit > 0: e_cursor = e_cursor.limit(limit)
    manual_expenses = await e_cursor.to_list(length=None)
    
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
        
    # Sort by date
    combined.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    
    # If no filter was applied, maybe we still want to limit total combined?
    if limit > 0:
        combined = combined[:limit]
        
    return combined

@router.get("/recent-transactions")
async def get_recent_transactions(
    current_user: dict = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """
    Get recent transactions using Receipts + Manual Expenses (Source of Truth)
    """
    user_id = current_user["user_id"]
    db = get_database()
    
    # Date Filtering
    date_query = {}
    if year and month:
        start_date = datetime(year, month, 1)
        if month == 12: end_date = datetime(year + 1, 1, 1)
        else: end_date = datetime(year, month + 1, 1)
        date_query = {"$gte": start_date, "$lt": end_date}
    
    # 1. Fetch Receipts (using date_extracted or uploaded_at)
    receipt_match = {"user_id": user_id}
    if date_query: receipt_match["date_extracted"] = date_query
    
    receipts = await db.receipts.find(receipt_match).sort("date_extracted", -1).limit(10).to_list(length=10)
    
    # 2. Fetch Manual Expenses (receipt_id: None)
    expense_match = {"user_id": user_id, "receipt_id": None}
    if date_query: expense_match["date"] = date_query
    
    manual_expenses = await db.expenses.find(expense_match).sort("date", -1).limit(10).to_list(length=10)
    
    combined = []
    
    for r in receipts:
        combined.append({
            "_id": str(r["_id"]),
            "type": "receipt",
            "description": r.get("merchant_name", "Unknown Merchant"),
            "amount": r.get("total_amount", 0.0),
            "date": r.get("date_extracted") or r.get("uploaded_at"),
            "category": "Shopping", # Default category for receipts header
            "receipt_id": str(r["_id"])
        })
        
    for e in manual_expenses:
        combined.append({
            "_id": str(e["_id"]),
            "type": "expense",
            "description": e.get("description", "Unknown"),
            "amount": e.get("amount", 0.0),
            "date": e.get("date"),
            "category": e.get("category", "Uncategorized"),
            "receipt_id": None
        })
    
    # Sort and slice top 5
    combined.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    return combined[:5]

@router.get("/summary")
async def get_expense_summary(
    current_user: dict = Depends(get_current_user),
    period: str = Query("all", enum=["month", "year", "all"]),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """
    Calculate totals from Receipts + Manual Expenses to ensure accuracy.
    """
    user_id = current_user["user_id"]
    db = get_database()
    
    # Date Filtering
    start_date = None
    end_date = None
    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month
    
    if period == "month":
        start_date = datetime(target_year, target_month, 1)
        if target_month == 12: year_end, month_end = target_year + 1, 1
        else: year_end, month_end = target_year, target_month + 1
        end_date = datetime(year_end, month_end, 1)
    elif period == "year":
        start_date = datetime(target_year, 1, 1)
        end_date = datetime(target_year + 1, 1, 1)
        
    date_query = {}
    if start_date: date_query = {"$gte": start_date, "$lt": end_date}
    
    # 1. From Receipts
    receipt_match = {"user_id": user_id}
    if date_query: receipt_match["date_extracted"] = date_query
    
    receipts = await db.receipts.find(receipt_match).to_list(None)
    
    # 2. From Manual Expenses
    expense_match = {"user_id": user_id, "receipt_id": None}
    if date_query: expense_match["date"] = date_query
    
    expenses = await db.expenses.find(expense_match).to_list(None)
    
    # Aggregate
    summary = {}
    
    for r in receipts:
        # For receipts, we use a single category "Shopping" or try to infer?
        # Since we are ignoring items, we lump the whole receipt total into one category.
        # Ideally, we would sum the items, but if items are messy, Total is safer.
        # Let's check if the receipt has a "category" field? receipts.py doesn't set it on the receipt doc usually.
        # Check if receipts logic has changed... receipts.py puts category in items.
        # For now, put receipt totals in "Shopping" or "Groceries" if inferred.
        # Or, we can query the expenses table ONLY for items linked to these receipts?
        # NO, user said items were messy. Using Receipt Total is safer for the "Total Spent" number.
        # But for Category Breakdown, this is less accurate.
        # HOWEVER, correctness of Total > Correctness of Category Breakdown.
        cat = "Shopping" # Default
        
        # Simple heuristic if available in merchant name
        m_lower = r.get("merchant_name", "").lower()
        if any(k in m_lower for k in ['food', 'bhat', 'cafe', 'restaurant']): cat = "Food"
        elif any(k in m_lower for k in ['mart', 'store', 'market']): cat = "Groceries"
        
        summary[cat] = summary.get(cat, 0) + r.get("total_amount", 0.0)
        
    for e in expenses:
        cat = e.get("category", "Uncategorized")
        summary[cat] = summary.get(cat, 0) + e.get("amount", 0.0)
        
    return [{"_id": k, "total": v} for k, v in summary.items()]

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
