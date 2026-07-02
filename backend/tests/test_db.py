import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_mongo():
    try:
        from app.database import check_db_connection, get_database
        await check_db_connection()
        print("DB Connection Check Passed")
        
        db = get_database()
        cols = await db.list_collection_names()
        print(f"Collections: {cols}")
        
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mongo())
