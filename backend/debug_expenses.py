import asyncio
from app.database import get_database
from datetime import datetime
import pprint

async def debug():
    db = get_database()
    print("--- LAST 5 EXPENSES ---")
    cursor = db.expenses.find().sort("_id", -1).limit(5)
    expenses = await cursor.to_list(None)
    
    with open("debug_log.txt", "w") as f:
        for e in expenses:
            f.write(f"ID: {e.get('_id')}\n")
            f.write(f"Desc: {e.get('description')}\n")
            f.write(f"Amount: {e.get('amount')} (Type: {type(e.get('amount'))})\n")
            f.write(f"Date: {e.get('date')} (Type: {type(e.get('date'))})\n")
            f.write(f"Category: {e.get('category')}\n")
            f.write("-" * 20 + "\n")

        f.write("\n--- SUMMARY QUERY TEST (Jan 2026) ---\n")
        start_date = datetime(2026, 1, 1)
        end_date = datetime(2026, 2, 1)
        
        pipeline = [
            {"$match": {"date": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}}
        ]
        result = await db.expenses.aggregate(pipeline).to_list(None)
        f.write(f"Aggregation Result: {result}\n")
    print("Debug completed, check debug_log.txt")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(debug())
