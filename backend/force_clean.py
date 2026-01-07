import asyncio
from app.database import get_database

async def force_clean():
    try:
        db = get_database()
        print("Force Cleaning...")
        
        # Delete
        await db.expenses.delete_many({})
        await db.receipts.delete_many({})
        
        # Verify
        count_ex = await db.expenses.count_documents({})
        count_rc = await db.receipts.count_documents({})
        
        print(f"Post-Cleanup Verification: Expenses={count_ex}, Receipts={count_rc}")
        
        if count_ex == 0 and count_rc == 0:
            print("SUCCESS: Database is empty.")
        else:
            print("WARNING: Database not empty!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(force_clean())
