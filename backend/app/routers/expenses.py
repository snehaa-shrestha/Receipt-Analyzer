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
    
    db = get_database()
    if expense.workspace_id:
        from bson import ObjectId
        workspace = await db.workspaces.find_one({"_id": ObjectId(expense.workspace_id)})
        if not workspace or not any(m["user_id"] == user_id for m in workspace.get("members", [])):
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
    
    if not expense.category or expense.category == "Uncategorized":
        expense.category = categorize_expense_rule_based(expense.description or "", expense.amount)
        
    db = get_database()
    new_expense = await db.expenses.insert_one(expense.model_dump())

    if expense.workspace_id:
        from app.routers.chat import manager
        await manager.broadcast_event(expense.workspace_id, "expense_update", {})

    return {"message": "Expense added", "id": str(new_expense.inserted_id)}

@router.get("/")
async def get_expenses(
    current_user: dict = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None,
    workspace_id: Optional[str] = None
):
    """
    Returns transactions (Merged Receipts + Manual Expenses).
    If year/month provided, returns ALL matching records.
    If no filter, returns recent 100.
    """
    user_id = current_user["user_id"]
    db = get_database()
    
    base_match = {}
    if workspace_id:
        from bson import ObjectId
        workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
        if not workspace or not any(m["user_id"] == current_user["user_id"] for m in workspace.get("members", [])):
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        base_match = {"workspace_id": workspace_id}
    else:
        base_match = {
            "user_id": user_id,
            "$or": [{"workspace_id": {"$exists": False}}, {"workspace_id": None}]
        }
    
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
    
    receipt_match = {**base_match}
    if date_query:
        date_or = {"$or": [
            {"date_extracted": date_query},
            {"date_extracted": {"$exists": False}, "uploaded_at": date_query},
            {"date_extracted": None, "uploaded_at": date_query},
        ]}
        receipt_match = {"$and": [{**base_match}, date_or]}
    
    r_cursor = db.receipts.find(receipt_match).sort("date_extracted", -1)
    if limit > 0: r_cursor = r_cursor.limit(limit)
    receipts = await r_cursor.to_list(length=None) # length=None is safe here as mongo driver handles it, or pass 10000
    
    expense_match = {"receipt_id": None, **base_match}
    if date_query: expense_match["date"] = date_query
    
    e_cursor = db.expenses.find(expense_match).sort("date", -1)
    if limit > 0: e_cursor = e_cursor.limit(limit)
    manual_expenses = await e_cursor.to_list(length=None)
    
    combined = []
    
    for r in receipts:
        items = r.get("items", [])
        receipt_category = r.get("category") or (items[0].get("category", "Shopping") if items else "Shopping")
        combined.append({
            "_id": str(r["_id"]),
            "type": "receipt",
            "description": r.get("merchant_name", "Unknown Merchant"),
            "amount": r.get("total_amount", 0.0),
            "date": r.get("date_extracted") or r.get("uploaded_at"),
            "category": receipt_category, 
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
    
    if limit > 0:
        combined = combined[:limit]
        
    return combined

@router.get("/recent-transactions")
async def get_recent_transactions(
    current_user: dict = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None,
    workspace_id: Optional[str] = None
):
    """
    Get recent transactions using Receipts + Manual Expenses (Source of Truth)
    """
    user_id = current_user["user_id"]
    db = get_database()
    
    base_match = {}
    if workspace_id:
        from bson import ObjectId
        workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
        if not workspace or not any(m["user_id"] == current_user["user_id"] for m in workspace.get("members", [])):
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        base_match = {"workspace_id": workspace_id}
    else:
        base_match = {
            "user_id": user_id,
            "$or": [{"workspace_id": {"$exists": False}}, {"workspace_id": None}]
        }
    
    date_query = {}
    if year and month:
        start_date = datetime(year, month, 1)
        if month == 12: end_date = datetime(year + 1, 1, 1)
        else: end_date = datetime(year, month + 1, 1)
        date_query = {"$gte": start_date, "$lt": end_date}
    
    receipt_match = {**base_match}
    if date_query:
        date_or = {"$or": [
            {"date_extracted": date_query},
            {"date_extracted": {"$exists": False}, "uploaded_at": date_query},
            {"date_extracted": None, "uploaded_at": date_query},
        ]}
        receipt_match = {"$and": [{**base_match}, date_or]}
    
    receipts = await db.receipts.find(receipt_match).sort("date_extracted", -1).limit(10).to_list(length=10)
    
    expense_match = {"receipt_id": None, **base_match}
    if date_query: expense_match["date"] = date_query
    
    manual_expenses = await db.expenses.find(expense_match).sort("date", -1).limit(10).to_list(length=10)
    
    combined = []
    
    for r in receipts:
        items = r.get("items", [])
        receipt_category = r.get("category") or (items[0].get("category", "Shopping") if items else "Shopping")
        combined.append({
            "_id": str(r["_id"]),
            "type": "receipt",
            "description": r.get("merchant_name", "Unknown Merchant"),
            "amount": r.get("total_amount", 0.0),
            "date": r.get("date_extracted") or r.get("uploaded_at"),
            "category": receipt_category,
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
    
    combined.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    return combined[:5]


@router.get("/summary")
async def get_expense_summary(
    current_user: dict = Depends(get_current_user),
    period: str = Query("all", enum=["month", "year", "all"]),
    year: Optional[int] = None,
    month: Optional[int] = None,
    workspace_id: Optional[str] = None
):
    """
    Calculate totals from Receipts + Manual Expenses to ensure accuracy.
    """
    user_id = current_user["user_id"]
    db = get_database()

    base_match = {}
    if workspace_id:
        from bson import ObjectId
        workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
        if not workspace or not any(m["user_id"] == current_user["user_id"] for m in workspace.get("members", [])):
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        base_match = {"workspace_id": workspace_id}
    else:
        base_match = {
            "user_id": user_id,
            "$or": [{"workspace_id": {"$exists": False}}, {"workspace_id": None}]
        }

    start_date = None
    end_date = None
    now = datetime.utcnow()
    target_year = year or now.year
    target_month = month or now.month

    if period == "month":
        start_date = datetime(target_year, target_month, 1)
        if target_month == 12:
            year_end, month_end = target_year + 1, 1
        else:
            year_end, month_end = target_year, target_month + 1
        end_date = datetime(year_end, month_end, 1)
    elif period == "year":
        start_date = datetime(target_year, 1, 1)
        end_date = datetime(target_year + 1, 1, 1)

    date_query = {}
    if start_date: date_query = {"$gte": start_date, "$lt": end_date}

    receipt_match = {**base_match}
    if date_query:
        date_or = {"$or": [
            {"date_extracted": date_query},
            {"date_extracted": {"$exists": False}, "uploaded_at": date_query},
            {"date_extracted": None, "uploaded_at": date_query},
        ]}
        receipt_match = {"$and": [{**base_match}, date_or]}
    
    receipts = await db.receipts.find(receipt_match).to_list(None)
    
    expense_match = {"receipt_id": None, **base_match}
    if date_query: expense_match["date"] = date_query
    
    expenses = await db.expenses.find(expense_match).to_list(None)

    summary = {}
    for r in receipts:
        items = r.get("items", [])
        cat = r.get("category") or (items[0].get("category", "Shopping") if items else "Shopping")
        summary[cat] = summary.get(cat, 0) + r.get("total_amount", 0.0)

    for e in expenses:
        cat = e.get("category", "Uncategorized")
        summary[cat] = summary.get(cat, 0) + e.get("amount", 0.0)

    return [{"_id": k, "total": v} for k, v in summary.items()]


@router.get("/forecast")
async def get_forecast(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    prediction = await predict_next_month_expenses(user_id, workspace_id)
    return prediction

@router.get("/export")
async def export_expenses(
    year: int = Query(None, description="Year to filter"),
    month: int = Query(None, description="Month to filter"),
    current_user: dict = Depends(get_current_user)
):
    from fastapi.responses import StreamingResponse
    import io
    import csv
    from datetime import datetime
    
    user_id = current_user["user_id"]
    db = get_database()
    
    query = {"user_id": user_id}
    if year and month:
        start_date = datetime(year, month, 1)
        if month == 12: end_date = datetime(year + 1, 1, 1)
        else: end_date = datetime(year, month + 1, 1)
        query["date"] = {"$gte": start_date, "$lt": end_date}
        
    expenses = await db.expenses.find(query).sort("date", -1).to_list(length=10000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    period_str = f"{year}-{month:02d}" if year and month else "All Time"
    writer.writerow(["Financial Export", f"Period: {period_str}"])
    writer.writerow([])
    
    writer.writerow(["Date", "Description", "Category", "Amount (Rs.)", "Source"])
    
    total_amount = 0.0
    for ex in expenses:
        source = "Receipt Scanner" if ex.get("receipt_id") else "Manual"
        amt = ex.get("amount", 0.0)
        total_amount += amt
        date_val = ex.get("date", "")
        if isinstance(date_val, datetime):
            date_val = date_val.strftime("%Y-%m-%d")
            
        writer.writerow([
            date_val,
            ex.get("description", ""),
            ex.get("category", ""),
            f"{amt:.2f}",
            source
        ])
        
    writer.writerow([])
    writer.writerow(["", "", "Total:", f"{total_amount:.2f}", ""])
        
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=expenses_export.csv"
    return response

@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    from bson import ObjectId
    
    try:
        oid = ObjectId(expense_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid expense ID")
        
    expense = await db.expenses.find_one({"_id": oid})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
        
    if expense.get("workspace_id"):
        workspace = await db.workspaces.find_one({"_id": ObjectId(expense["workspace_id"])})
        is_admin = False
        if workspace:
            is_admin = any(m["user_id"] == current_user["user_id"] and m["role"] == "admin" for m in workspace.get("members", []))
        if expense["user_id"] != current_user["user_id"] and not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to delete this expense")
    elif expense["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")
        
    result = await db.expenses.delete_one({"_id": oid})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")

    ws_id = expense.get("workspace_id")
    if ws_id:
        from app.routers.chat import manager
        await manager.broadcast_event(ws_id, "expense_update", {})

    return {"message": "Expense deleted"}
