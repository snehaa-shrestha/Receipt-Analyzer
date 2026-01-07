import asyncio
from app.database import get_database
from datetime import datetime

async def clean_future_expenses():
    db = get_database()
    
    # Simple check for any expense with year > 2030 (VS dates like 2082)
    # We will delete them to clean up the duplicates
    start_future = datetime(2030, 1, 1)
    
    result = await db.expenses.delete_many({"date": {"$gt": start_future}})
    print(f"Deleted {result.deleted_count} expenses with future dates (VS 2082 etc).")
    
    # Also clean up Receipts if needed (not strictly linked but good for hygiene)
    # Note: Receipts store 'date_extracted'.
    r_result = await db.receipts.delete_many({"date_extracted": {"$gt": start_future}})
    print(f"Deleted {r_result.deleted_count} receipts with future dates.")
    
    # Also delete duplicate uploads of "KsMATA" / "ESTIMATE" if simpler
    # But date filter should catch them.

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(clean_future_expenses())
