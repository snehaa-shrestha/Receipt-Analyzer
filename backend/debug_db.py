import asyncio
from app.database import get_database

async def inspect_db():
    try:
        db = get_database()
        print("--- Inspecting Expenses ---")
        
        # 1. Total Count
        count = await db.expenses.count_documents({})
        print(f"Total Expense Records: {count}")
        
        # 2. Total Sum
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
        agg = await db.expenses.aggregate(pipeline).to_list(1)
        total = agg[0]['total'] if agg else 0
        print(f"Total Sum: {total:,.2f}")
        
        # 3. Top 5 Largest
        print("--- Top 5 Largest Expenses ---")
        cursor = db.expenses.find({}).sort("amount", -1).limit(5)
        async for doc in cursor:
            print(f"Amount: {doc.get('amount', 0):,.2f} | Desc: {doc.get('description')} | Date: {doc.get('date')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(inspect_db())
