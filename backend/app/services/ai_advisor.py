"""
AI Financial Advisor Service
Provides personalized financial advice based on user transaction data
"""

from app.database import get_database
from datetime import datetime, timedelta
import os

async def get_financial_advice(user_id: str):
    """
    Generate financial advice for a user based on their spending patterns
    """
    try:
        db = get_database()
        
        # Get user's recent expenses (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        expenses = await db.expenses.find({
            "user_id": user_id,
            "date": {"$gte": thirty_days_ago}
        }).to_list(length=1000)
        
        # Calculate basic statistics
        total_spent = sum(e.get("amount", 0) for e in expenses)
        expense_count = len(expenses)
        
        # Get category breakdown
        category_totals = {}
        for expense in expenses:
            category = expense.get("category", "Uncategorized")
            category_totals[category] = category_totals.get(category, 0) + expense.get("amount", 0)
        
        # Generate advice based on spending patterns
        advice_text = generate_advice_text(total_spent, expense_count, category_totals)
        
        return {
            "raw_advice": advice_text,
            "total_spent_30days": total_spent,
            "transaction_count": expense_count,
            "category_breakdown": category_totals,
            "mock": not bool(os.getenv("OPENAI_API_KEY"))
        }
        
    except Exception as e:
        print(f"[AI ADVISOR ERROR] {e}")
        return {
            "raw_advice": "Unable to generate advice at this time. Please try again later.",
            "error": str(e),
            "mock": True
        }


def generate_advice_text(total_spent: float, transaction_count: int, categories: dict) -> str:
    """Generate personalized financial advice text"""
    
    advice = []
    
    # Overall spending analysis
    advice.append(f"📊 **Spending Overview (Last 30 Days)**")
    advice.append(f"You've spent ${total_spent:.2f} across {transaction_count} transactions.")
    advice.append("")
    
    # Category analysis
    if categories:
        advice.append("💰 **Category Breakdown:**")
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for category, amount in sorted_categories[:5]:
            percentage = (amount / total_spent * 100) if total_spent > 0 else 0
            advice.append(f"  • {category}: ${amount:.2f} ({percentage:.1f}%)")
        advice.append("")
    
    # Personalized recommendations
    advice.append("💡 **Recommendations:**")
    
    if categories:
        top_category, top_amount = sorted_categories[0]
        advice.append(f"1. Your highest spending is in {top_category} (${top_amount:.2f}). Consider setting a budget limit for this category.")
    
    avg_per_transaction = total_spent / transaction_count if transaction_count > 0 else 0
    advice.append(f"2. Your average transaction is ${avg_per_transaction:.2f}. Track small purchases to avoid overspending.")
    
    advice.append("3. Set up category-specific budgets to better control your expenses.")
    advice.append("4. Review your spending weekly to stay on track with your financial goals.")
    
    advice.append("")
    advice.append("✨ *This is a basic analysis. For AI-powered insights, add your OpenAI API key to the backend .env file.*")
    
    return "\n".join(advice)
