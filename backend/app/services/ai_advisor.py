"""
AI Financial Advisor Service
Provides personalized financial advice based on user transaction data
"""

from app.database import get_database
from datetime import datetime, timedelta
import os

import os
import google.generativeai as genai
from app.database import get_database
from datetime import datetime, timedelta

async def get_financial_advice(user_id: str, year: int = None, month: int = None):
    """
    Generate financial advice using Gemini AI based on transaction data.
    Supports filtering by specific month/year.
    """
    try:
        print("[AI] Initializing Gemini Service...")
        db = get_database()
        
        if year and month:
            start_date = datetime(year, month, 1)
            if month == 12: end_date = datetime(year + 1, 1, 1)
            else: end_date = datetime(year, month + 1, 1)
            
            date_filter = {"$gte": start_date, "$lt": end_date}
            period_str = f"{datetime(year, month, 1).strftime('%B %Y')}"
            print(f"[AI] Fetching data for period: {period_str}")
        else:
            start_date = datetime.utcnow() - timedelta(days=30)
            date_filter = {"$gte": start_date}
            period_str = "Last 30 Days"
            print(f"[AI] Fetching data for period: {period_str}")
        
        receipt_query = {"user_id": user_id, "date_extracted": date_filter}
        receipts = await db.receipts.find(receipt_query).to_list(length=1000)
        
        expense_query = {"user_id": user_id, "receipt_id": None, "date": date_filter}
        manual = await db.expenses.find(expense_query).to_list(length=1000)
        
        print(f"[AI] Found {len(receipts)} receipts and {len(manual)} manual expenses.")

        transactions = []
        for r in receipts:
            transactions.append({
                "description": r.get("merchant_name", "Unknown"),
                "amount": r.get("total_amount", 0.0),
                "date": r.get("date_extracted"),
                "category": "Receipt"
            })
        for e in manual:
            transactions.append({
                "description": e.get("description", "Unknown"),
                "amount": e.get("amount", 0.0),
                "date": e.get("date"),
                "category": e.get("category", "Uncategorized")
            })
            
        total_spent = sum(t["amount"] for t in transactions)
        count = len(transactions)
        
        categories = {}
        for t in transactions:
            cat = t.get("category", "Uncategorized")
            categories[cat] = categories.get(cat, 0) + t.get("amount", 0)
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[AI] No API Key found.")
            return {
                "raw_advice": "Please configure GEMINI_API_KEY in backend .env to enable AI insights.",
                "mock": True
            }
            
        print("[AI] Sending data to Gemini...")
        genai.configure(api_key=api_key)
        
        models_to_try = [
            'gemini-2.5-flash',       
            'gemini-1.5-flash',       
            'gemini-1.5-flash-latest',
            'gemini-pro',
            'gemini-flash-latest'
        ]
        
        advice_text = None
        used_model = None
        error_details = []

        
        tx_list_str = "\n".join([
            f"{t['date'].strftime('%Y-%m-%d') if t['date'] else 'N/A'}: {t['description']} ({t.get('category','Uncat')}) - {t['amount']}"
            for t in transactions[:500] # Pass up to 500 recent transactions as context
        ])

        prompt = f"""
You are a smart personal finance assistant.

Analyze the user's spending data for the period: {period_str}.

SUMMARY
- Total Spent: {total_spent}
- Transaction Count: {count}
- Category Breakdown:
{categories}

TRANSACTIONS
{tx_list_str}

INSTRUCTIONS
- Analyze only the provided data.
- Do not make assumptions if there is insufficient information.
- Keep the analysis concise, practical, and easy to understand.
- Use short bullet points instead of long paragraphs.
- Each bullet should contain only one idea.
- Avoid repeating the same information.
- Mention percentages where appropriate.
- Highlight the largest expense.
- If only a few transactions are available, clearly state that more data is needed for meaningful trend analysis.

FORMATTING RULES
- Output must be plain text only.
- Do NOT use Markdown.
- Do NOT use bold, italics, emojis, or special formatting.
- Use UPPERCASE section headings.
- Use "-" for bullet points.
- Keep the total response under 180 words.

OUTPUT FORMAT

ANALYSIS PERIOD
{period_str}

OVERVIEW
Total Spent: {total_spent}
Transactions: {count}
Top Category: [category]
Highest Expense: [merchant] (Rs. [amount])

SPENDING PATTERN
- Describe the overall spending behavior.
- Mention whether spending is concentrated or diversified.
- Mention any noticeable trends.

KEY INSIGHTS
- Insight 1
- Insight 2
- Insight 3

UNUSUAL ACTIVITY
- Mention any unusually large transactions.
- If none exist, say "No unusual spending detected."

RECOMMENDATIONS
- Recommendation 1
- Recommendation 2
- Recommendation 3

Remember:
- Base every statement only on the supplied transactions.
- If the dataset is too small, say so instead of inventing trends.
- Be clear, helpful, and concise.
"""

        for model_name in models_to_try:
            try:
                print(f"[AI] Attempting model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt) 
                advice_text = response.text
                used_model = model_name
                print(f"[AI] Success with {model_name}")
                break
            except Exception as e:
                print(f"[AI] Failed with {model_name}: {str(e)}")
                error_details.append(f"{model_name}: {str(e)}")
                continue
        
        if not advice_text:
            raise Exception(f"All models failed. Details: {'; '.join(error_details)}")

        print("[AI] Advice generated successfully using " + str(used_model))
        
        return {
            "raw_advice": advice_text,
            "total_spent": total_spent, 
            "mock": False,
            "used_model": used_model
        }

    except Exception as e:
        print(f"[AI] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"raw_advice": "AI Service currently unavailable.", "error": str(e), "mock": True}

def generate_advice_text(total, count, cats):
    return "Legacy method removed."
