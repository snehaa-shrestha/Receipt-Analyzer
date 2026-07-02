import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Redirect to file
output_file = open("monthly_check.txt", "w", encoding="utf-8")
sys.stdout = output_file

async def check_monthly_calculation():
    """Check what the monthly calculation is returning"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.receipt_analyzer
    
    # Get user 'ram'
    user = await db.users.find_one({"username": "ram"})
    if not user:
        print("User 'ram' not found")
        return
    
    user_id = str(user["_id"])
    print(f"User: {user.get('username')}")
    print(f"Monthly Budget: ${user.get('monthly_budget', 0):,.2f}")
    print("=" * 80)
    
    # Calculate current month range
    now = datetime.utcnow()
    target_year = now.year
    target_month = now.month
    
    start_date = datetime(target_year, target_month, 1)
    if target_month == 12:
        year_end, month_end = target_year + 1, 1
    else:
        year_end, month_end = target_year, target_month + 1
    end_date = datetime(year_end, month_end, 1)
    
    print(f"\nCurrent Month Range:")
    print(f"  Start: {start_date}")
    print(f"  End: {end_date}")
    print(f"  (UTC Time Now: {now})")
    
    # Get expenses for current month
    exp_match = {"user_id": user_id, "date": {"$gte": start_date, "$lt": end_date}}
    expenses = await db.expenses.find(exp_match).to_list(length=1000)
    
    print(f"\nExpenses in Current Month: {len(expenses)}")
    
    total = 0
    by_category = {}
    
    for e in expenses:
        amount = float(e.get("amount") or 0)
        if amount > 0:
            total += amount
            cat = e.get("category", "Uncategorized")
            by_category[cat] = by_category.get(cat, 0) + amount
            print(f"  - {e.get('description')}: ${amount:,.2f} [{cat}] (Date: {e.get('date')})")
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL SPENT THIS MONTH: ${total:,.2f}")
    print(f"{'=' * 80}")
    
    print(f"\nBreakdown by Category:")
    for cat, amt in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: ${amt:,.2f}")
    
    budget = user.get('monthly_budget', 0)
    remaining = budget - total
    
    print(f"\n{'=' * 80}")
    print(f"Monthly Budget: ${budget:,.2f}")
    print(f"Spent This Month: ${total:,.2f}")
    if remaining >= 0:
        print(f"Remaining: ${remaining:,.2f}")
    else:
        print(f"Overspent: ${abs(remaining):,.2f}")
    print(f"{'=' * 80}")
    
    # Check all expenses (not just this month)
    all_expenses = await db.expenses.find({"user_id": user_id}).to_list(length=10000)
    all_total = sum(float(e.get("amount") or 0) for e in all_expenses if e.get("amount") and e.get("amount") > 0)
    print(f"\nAll-Time Total (for comparison): ${all_total:,.2f}")
    
    client.close()
    output_file.close()
    print("Output written to monthly_check.txt", file=sys.__stdout__)

if __name__ == "__main__":
    asyncio.run(check_monthly_calculation())
