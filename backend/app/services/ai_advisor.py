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
        
        # 1. Determine Date Range
        if year and month:
            start_date = datetime(year, month, 1)
            if month == 12: end_date = datetime(year + 1, 1, 1)
            else: end_date = datetime(year, month + 1, 1)
            
            date_filter = {"$gte": start_date, "$lt": end_date}
            period_str = f"{datetime(year, month, 1).strftime('%B %Y')}"
            print(f"[AI] Fetching data for period: {period_str}")
        else:
            # Default: Last 30 days
            start_date = datetime.utcnow() - timedelta(days=30)
            date_filter = {"$gte": start_date}
            period_str = "Last 30 Days"
            print(f"[AI] Fetching data for period: {period_str}")
        
        # 2. Fetch Data (Receipts + Manual Expenses)
        # Receipts
        receipt_query = {"user_id": user_id, "date_extracted": date_filter}
        receipts = await db.receipts.find(receipt_query).to_list(length=1000)
        
        # Manual Expenses
        expense_query = {"user_id": user_id, "receipt_id": None, "date": date_filter}
        manual = await db.expenses.find(expense_query).to_list(length=1000)
        
        print(f"[AI] Found {len(receipts)} receipts and {len(manual)} manual expenses.")

        # Combine data
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
            
        # Stats
        total_spent = sum(t["amount"] for t in transactions)
        count = len(transactions)
        
        # Category Breakdown
        categories = {}
        for t in transactions:
            cat = t.get("category", "Uncategorized")
            categories[cat] = categories.get(cat, 0) + t.get("amount", 0)
            
        # 3. Check for API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[AI] No API Key found.")
            return {
                "raw_advice": "Please configure GEMINI_API_KEY in backend .env to enable AI insights.",
                "mock": True
            }
            
        # 4. Call Gemini with Fallback
        print("[AI] Sending data to Gemini...")
        genai.configure(api_key=api_key)
        
        # List of models to try in order of preference
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

        # Prepare dense transaction list for LLM context
        # Format: "YYYY-MM-DD: Description (Category) - $Amount"
        tx_list_str = "\n".join([
            f"{t['date'].strftime('%Y-%m-%d') if t['date'] else 'N/A'}: {t['description']} ({t.get('category','Uncat')}) - {t['amount']}"
            for t in transactions[:500] # Pass up to 500 recent transactions as context
        ])

        prompt = f"""
        Act as a highly capable, expert financial advisor. 
        Perform a COMPREHENSIVE deep-dive analysis of the following spending data for the period: {period_str}.
        
        SUMMARY DATA:
        - Total Spent: {total_spent}
        - Transaction Count: {count}
        - Category Breakdown: {categories}
        
        FULL TRANSACTION HISTORY:
        {tx_list_str}
        
        INSTRUCTIONS:
        1. Analyze the spending patterns deeply. Identify specific trends.
        2. Provide 3-4 detailed, actionable, and personalized insights.
        3. Flag any specific high-value transactions that look unusual.
        
        FORMATTING RULES (EXTREMELY STRICT):
        - OUTPUT MUST BE PLAIN TEXT ONLY.
        - NO Markdown characters allowed (NO '#', NO '*', NO '**', NO '`').
        - NO Emojis allowed.
        - Use UPPERCASE for section headers.
        - Use standard dashes (-) for bullet points.
        - Do not use bold or italic text.
        
        REQUIRED OUTPUT FORMAT:
        
        ANALYSIS PERIOD: [Month Year]
        
        SUMMARY AND PATTERNS
        [Your deep analysis of the spending patterns here...]
        
        KEY INSIGHTS
        - [Insight 1]
        - [Insight 2]
        - [Insight 3]
        
        UNUSUAL ACTIVITY
        [Details on flagged transactions...]
        
        RECOMMENDATIONS
        [Specific advice...]
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
