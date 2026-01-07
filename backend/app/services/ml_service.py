from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.database import get_database

async def predict_next_month_expenses(user_id: str):
    db = get_database()
    
    # 1. Fetch Expenses (Last 12 months)
    expenses = await db.expenses.find({"user_id": user_id}).to_list(length=5000)
    
    if not expenses:
        return {"predicted_amount": 0.0, "advice": "Start tracking expenses to see AI forecasts!"}

    df = pd.DataFrame(expenses)
    df['date'] = pd.to_datetime(df['date'])
    
    # 2. Add Current Month Projection
    now = datetime.utcnow()
    current_month_start = datetime(now.year, now.month, 1)
    days_in_current_month = (current_month_start.replace(month=now.month % 12 + 1) - timedelta(days=1)).day
    days_passed = max(1, now.day)
    
    current_month_expenses = df[df['date'] >= current_month_start]['amount'].sum()
    
    # Calculate "Velocity" (Spending per day)
    current_velocity = current_month_expenses / days_passed
    projected_current_month = current_velocity * days_in_current_month
    
    # 3. Analyze Historical Momentum (Past 3-6 months)
    # We treat spending as a 'moving object' with momentum
    df['month_key'] = df['date'].dt.to_period('M')
    monthly_totals = df.groupby('month_key')['amount'].sum().sort_index()
    
    # Filter out current partial month from history to avoid skewing
    # history = monthly_totals[monthly_totals.index < pd.Period(now, freq='M')]
    # Use string comparison to be safe with different pandas versions
    current_period = pd.Period(now, freq='M')
    history = monthly_totals[monthly_totals.index < current_period]
    
    if len(history) < 2:
        # Not enough history for momentum, use pure current velocity projection
        prediction = projected_current_month
        msg = "Based on your current daily spending velocity."
    else:
        # Calculate Weighted Moving Average (Momentum)
        # Give more weight to recent months (Physics: recent force has more impact)
        recent_months = history.tail(3)
        weights = np.arange(1, len(recent_months) + 1)
        weighted_avg = np.average(recent_months.values, weights=weights)
        
        # Combine projected current month with historical momentum
        # If we are effectively AT the end of the month, current velocity is truth.
        # If early in month, rely more on history.
        progress_ratio = min(1.0, days_passed / days_in_current_month)
        
        # Formula: Prediction = (Current Projection * weight) + (Historical Momentum * weight)
        # As month progresses, 'Current Projection' gains 'mass' (reliability)
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
