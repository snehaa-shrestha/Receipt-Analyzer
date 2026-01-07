import asyncio
from app.database import get_database
from datetime import datetime

async def debug_budget():
    db = get_database()
    
    now = datetime.utcnow()
    print(f"Current UTC time: {now}")
    print(f"Current month: {now.month}, Current year: {now.year}")
    
    # Check receipts
    print("\n=== RECEIPTS ===")
    receipts = await db.receipts.find({}).sort("date_extracted", -1).limit(5).to_list(5)
    for r in receipts:
        print(f"Merchant: {r.get('merchant_name')}, Amount: {r.get('total_amount')}, Date: {r.get('date_extracted')}")
    
    # Check manual expenses
    print("\n=== MANUAL EXPENSES ===")
    expenses = await db.expenses.find({"receipt_id": None}).sort("date", -1).limit(5).to_list(5)
    for e in expenses:
        print(f"Desc: {e.get('description')}, Amount: {e.get('amount')}, Date: {e.get('date')}, Category: {e.get('category')}")
    
    # Test summary aggregation for current month
    print("\n=== CURRENT MONTH SUMMARY ===")
    start_date = datetime(now.year, now.month, 1)
    if now.month == 12:
        end_date = datetime(now.year + 1, 1, 1)
    else:
        end_date = datetime(now.year, now.month + 1, 1)
    
    print(f"Date range: {start_date} to {end_date}")
    
    # Manual expenses
    exp_pipeline = [
        {"$match": {"receipt_id": None, "date": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
    ]
    exp_result = await db.expenses.aggregate(exp_pipeline).to_list(None)
    print(f"Manual Expenses: {exp_result}")
    
    # Receipts
    rcpt_pipeline = [
        {"$match": {"date_extracted": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "Receipts", "total": {"$sum": "$total_amount"}}}
    ]
    rcpt_result = await db.receipts.aggregate(rcpt_pipeline).to_list(None)
    print(f"Receipts: {rcpt_result}")
    
    # Calculate total
    total = sum(r["total"] for r in exp_result) + sum(r["total"] for r in rcpt_result)
    print(f"\nTOTAL SPENT THIS MONTH: {total}")

if __name__ == "__main__":
    asyncio.run(debug_budget())
