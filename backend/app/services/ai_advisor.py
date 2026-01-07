import openai
import os
from app.database import get_database
from datetime import datetime, timedelta
from bson import ObjectId
from dotenv import load_dotenv

# Ensure env vars are loaded
load_dotenv()

async def get_financial_advice(user_id: str):
    # Initialize OpenAI (API Key from env)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    db = get_database()
    
    # 1. Gather Data (Last 30 Days)
    now = datetime.utcnow()
    last_30 = now - timedelta(days=30)
    
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$gte": last_30}}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}}
    ]
    
    spending_data = await db.expenses.aggregate(pipeline).to_list(None)
    
    # Fallback: If no data in last 30 days, try All Time (or last 365 days)
    if not spending_data:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
            {"$sort": {"total": -1}}
        ]
        spending_data = await db.expenses.aggregate(pipeline).to_list(None)

    if not spending_data:
        return {
            "raw_advice": "### No Data Available\n\nI can't see any expenses yet! Start by uploading your first receipt or adding an expense manually.\n\nOnce you have some data, I'll be able to provide spending analysis and budget tips."
        }
        
    total_spent = sum(item["total"] for item in spending_data)
    
    # Get User Budget
    user = None
    try:
        from bson import ObjectId
        if ObjectId.is_valid(user_id):
            user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        pass
        
    budget = user.get("monthly_budget", 0) if user else 0
    
    # 2. Format Data for Prompt
    summary_text = f"Total Spent (Sample): ${total_spent:.2f}\n"
    if budget > 0:
        summary_text += f"Monthly Budget: ${budget:.2f}\n"
        
    summary_text += "Spending by Category:\n"
    for item in spending_data:
        cat = item["_id"] or "Uncategorized"
        amt = item["total"]
        summary_text += f"- {cat}: ${amt:.2f}\n"
        
    # 3. Call OpenAI
    if not openai.api_key:
        # Mock advice if no key
        top_cat = spending_data[0]["_id"] if spending_data else "None"
        return {
            "mock": True,
            "raw_advice": f"### Analysis\nYou are spending most on **{top_cat}**.\n\n### Savings Tips\nConsider setting a limit for {top_cat}.\n\n### Note\nConfigure OpenAI API Key in backend .env for real personalized advice."
        }
        
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a concise financial advisor. Analyze the user's spending data. Provide 3 short sections in Markdown: 'Analysis' (where they spend most), 'Savings Tips' (where to cut), and 'Budget Advice'."},
                {"role": "user", "content": f"Here is my data:\n{summary_text}\nPlease advise."}
            ],
            max_tokens=400
        )
        
        advice_text = response.choices[0].message.content
        return {"raw_advice": advice_text}
        
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {"raw_advice": f"### Error\n\nFailed to reach AI service: {str(e)}", "error": str(e)}
