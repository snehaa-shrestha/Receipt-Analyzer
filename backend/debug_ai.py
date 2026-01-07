import asyncio
from app.database import get_database
from datetime import datetime, timedelta
from bson import ObjectId

async def debug_ai():
    db = get_database()
    
    # List all users
    users = await db.users.find().to_list(10)
    print(f"Users found: {len(users)}")
    for u in users:
        print(f"User: {u['_id']} / {u.get('username')}")
        
        # Check expenses for this user
        uid = str(u["_id"])
        
        # 1. Check count
        count = await db.expenses.count_documents({"user_id": uid})
        print(f"  Total Expenses: {count}")
        
        # 2. Check dates
        expenses = await db.expenses.find({"user_id": uid}).limit(5).to_list(5)
        for e in expenses:
            print(f"    - {e.get('description')}: {e.get('date')} (Type: {type(e.get('date'))})")
            
        # 3. Test Pipeline
        now = datetime.utcnow()
        last_30 = now - timedelta(days=30)
        pipeline = [
            {"$match": {"user_id": uid, "date": {"$gte": last_30}}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        ]
        res = await db.expenses.aggregate(pipeline).to_list(None)
        print(f"  Pipeline Result (Last 30d): {res}")

if __name__ == "__main__":
    asyncio.run(debug_ai())
