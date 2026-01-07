from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.database import get_database

async def predict_next_month_expenses(user_id: str):
    db = get_database()
    
    # Fetch all user expenses
    expenses = await db.expenses.find({"user_id": user_id}).to_list(length=1000)
    
    if len(expenses) < 5:
        return {"prediction": 0.0, "message": "Not enough data for prediction (min 5 records)"}
        
    df = pd.DataFrame(expenses)
    df['date'] = pd.to_datetime(df['date'])
    df['month_key'] = df['date'].dt.to_period('M').astype(int) # Convert to integer for regression
    
    # Aggregate by month
    monthly_spending = df.groupby('month_key')['amount'].sum().reset_index()
    
    if len(monthly_spending) < 2:
         return {"prediction": monthly_spending['amount'].mean(), "message": "Not enough months for trend analysis, using average."}

    X = monthly_spending[['month_key']].values
    y = monthly_spending['amount'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict next month
    next_month_key = X[-1][0] + 1
    prediction = model.predict([[next_month_key]])[0]
    
    return {
        "prediction": max(0.0, float(prediction)), # No negative spending
        "trend": "increasing" if model.coef_[0] > 0 else "decreasing",
        "confidence": "moderate" # Placeholder
    }

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
