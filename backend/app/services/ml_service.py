from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.database import get_database

async def predict_next_month_expenses(user_id: str, workspace_id: str = None, category: str = None):
    db = get_database()
    
    base_match = {}
    if workspace_id:
        from bson import ObjectId
        workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
        if not workspace or not any(m["user_id"] == user_id for m in workspace.get("members", [])):
            return {"predicted_amount": 0.0, "advice": "Not authorized to view ML forecast for this workspace."}
        base_match = {"workspace_id": workspace_id}
    else:
        base_match = {"user_id": user_id, "$or": [{"workspace_id": None}, {"workspace_id": {"$exists": False}}]}
        
    receipts = await db.receipts.find({**base_match}).to_list(length=5000)
    manual_expenses = await db.expenses.find({**base_match, "receipt_id": None}).to_list(length=5000)
    
    data = []
    for r in receipts:
        items = r.get("items", [])
        receipt_category = r.get("category") or r.get("suggested_category") or (items[0].get("category", "Shopping") if items else "Shopping")
        if category and receipt_category != category:
            continue
        data.append({
            "date": r.get("date_extracted") or r.get("uploaded_at"),
            "amount": r.get("total_amount", 0.0)
        })
        
    for e in manual_expenses:
        expense_category = e.get("category", "Uncategorized")
        if category and expense_category != category:
            continue
        data.append({
            "date": e.get("date"),
            "amount": e.get("amount", 0.0)
        })
    
    if not data:
        if category:
            return {"predicted_amount": 0.0, "advice": f"Not enough data to forecast for {category}."}
        return {"predicted_amount": 0.0, "advice": "Start tracking expenses to see AI forecasts!"}

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    
    if df.empty:
        return {"predicted_amount": 0.0, "advice": "Not enough valid expense dates to forecast."}

    now = datetime.utcnow()
    current_month_start = datetime(now.year, now.month, 1)
    days_in_current_month = (current_month_start.replace(month=now.month % 12 + 1) - timedelta(days=1)).day
    days_passed = max(1, now.day)
    
    current_month_expenses = df[df['date'] >= current_month_start]['amount'].sum()
    
    current_velocity = current_month_expenses / days_passed
    projected_current_month = current_velocity * days_in_current_month
    
    df['month_key'] = df['date'].dt.to_period('M')
    monthly_totals = df.groupby('month_key')['amount'].sum().sort_index()
    
    current_period = pd.Period(now, freq='M')
    history = monthly_totals[monthly_totals.index < current_period]
    
    if len(history) < 2:
        prediction = projected_current_month
        msg = "Based on your current daily spending velocity."
    else:
        recent_months = history.tail(3)
        weights = np.arange(1, len(recent_months) + 1)
        weighted_avg = np.average(recent_months.values, weights=weights)
        
        progress_ratio = min(1.0, days_passed / days_in_current_month)
        
        prediction = (projected_current_month * progress_ratio) + (weighted_avg * (1 - progress_ratio))
        msg = "Calculated using spending momentum and current velocity."

    return {
        "predicted_amount": float(prediction),
        "advice": generate_smart_advice(prediction, current_month_expenses, days_passed),
        "details": {
            "current_velocity": f"${current_velocity:.2f}/day",
            "projected_total": float(projected_current_month)
        }
    }

def generate_smart_advice(prediction, current_spent, days_passed):
    if days_passed < 7:
        return "Early in the month! Keep your daily velocity low to stay on track."
    elif current_spent > (prediction * 0.8):
        return "Warning: High velocity detected! You're burning through budget fast."
    else:
        return "Great job! Your spending momentum is stable."

def classify_text(text: str) -> str:
    text = text.lower()
    if any(x in text for x in ['uber', 'lyft', 'taxi', 'bus', 'train', 'fuel', 'gas', 'shell', 'bp']):
        return "Transport"
    if any(x in text for x in ['food', 'restaurant', 'burger', 'pizza', 'cafe', 'coffee', 'starbucks', 'mcdonalds', 'kfc', 'dining', 'lunch', 'dinner']):
        return "Food"
    if any(x in text for x in ['walmart', 'target', 'amazon', 'shop', 'store', 'cloth', 'shoe', 'nike', 'adidas', 'mall', 'bhat', 'mart', 'sales', 'market']):
        return "Shopping"
    if any(x in text for x in ['netflix', 'hulu', 'spotify', 'cinema', 'game', 'playstation', 'xbox']):
        return "Entertainment"
    if any(x in text for x in ['bill', 'utility', 'electric', 'water', 'rent', 'internet', 'phone']):
        return "Bills"
    if any(x in text for x in ['drug', 'pharmacy', 'doctor', 'hospital', 'cvs', 'walgreens']):
        return "Health"
    return "Other"

def categorize_expense_rule_based(description: str, amount: float):
    return classify_text(description)
