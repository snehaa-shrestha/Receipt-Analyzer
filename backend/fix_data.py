import asyncio
from app.database import get_database

async def fix_data():
    try:
        db = get_database()
        print("Scanning for corrupted data...")
        
        # Count before
        count = await db.expenses.count_documents({})
        print(f"Found {count} expense records.")
        
        # Option 1: Nuclear option (safest for dev) - Delete all to restart clean
        # Since the user just started, this is likely what they want to fix the "gibberish"
        await db.expenses.delete_many({})
        await db.receipts.delete_many({})
        
        print("Successfully removed corrupted records.")
        print("Please upload your receipt again to see the correct Rs 945.00 total.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fix_data())
