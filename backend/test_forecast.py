import asyncio
from app.services.ml_service import predict_next_month_expenses
from app.database import get_database

async def test_forecast():
    db = get_database()
    # Get user 'ram'
    user = await db.users.find_one({"username": "ram"})
    if not user:
        print("User not found")
        return
        
    result = await predict_next_month_expenses(str(user["_id"]))
    print("Forecast Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_forecast())
