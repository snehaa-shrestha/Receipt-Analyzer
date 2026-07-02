from app.database import get_database
from datetime import datetime, timedelta
from bson import ObjectId

async def update_monthly_streak(user_id: str):
    db = get_database()
    try:
        user_oid = ObjectId(user_id)
    except:
        return

    user = await db.users.find_one({"_id": user_oid})
    if not user:
        return
        
    last_active_str = user.get("last_active_month") # e.g. "2026-01"
    now = datetime.utcnow()
    current_month_str = now.strftime("%Y-%m")
    
    
    if not last_active_str:
        await db.users.update_one(
            {"_id": user_oid}, 
            {"$set": {"streak_count": 1, "last_active_month": current_month_str}}
        )
        return

    if last_active_str == current_month_str:
        return # Already active this month

    last_date = datetime.strptime(last_active_str, "%Y-%m")
    first_of_current = datetime(now.year, now.month, 1)
    expected_prev = (first_of_current - timedelta(days=1)).replace(day=1)
    expected_prev_str = expected_prev.strftime("%Y-%m")

    if last_active_str == expected_prev_str:
        await db.users.update_one(
            {"_id": user_oid}, 
            {"$inc": {"streak_count": 1}, "$set": {"last_active_month": current_month_str}}
        )
    else:
        await db.users.update_one(
            {"_id": user_oid}, 
            {"$set": {"streak_count": 1, "last_active_month": current_month_str}}
        )

async def check_and_update_quests(user_id: str):
    db = get_database()
    try:
        user_oid = ObjectId(user_id)
    except:
        return [], 0

    user = await db.users.find_one({"_id": user_oid})
    if not user:
        return [], 0

    completed_quests = user.get("completed_quests", [])
    current_points = user.get("points", 0)
    
    quests = [
        {"id": 101, "title": "Receipt Rookie", "description": "Upload at least 5 receipts", "points": 100},
        {"id": 102, "title": "Savvy Saver", "description": "Spend less than 80% of your monthly budget", "points": 150},
        {"id": 103, "title": "Expense Explorer", "description": "Have 5 categorized expenses (not Uncategorized)", "points": 200}
    ]
    
    updates = {}
    points_to_add = 0
    
    if 101 not in completed_quests:
        receipt_count = await db.receipts.count_documents({"user_id": user_id})
        if receipt_count >= 5:
            completed_quests.append(101)
            points_to_add += quests[0]["points"]

    if 102 not in completed_quests:
        current_month = datetime.utcnow().month
        current_year = datetime.utcnow().year
        
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "date": {"$gte": datetime(current_year, current_month, 1)}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        spent_result = await db.expenses.aggregate(pipeline).to_list(length=1)
        total_spent = spent_result[0]["total"] if spent_result else 0
        
        global_budget = user.get("monthly_budget", 0)
        
        if global_budget > 0:
            if total_spent > 0 and total_spent <= (global_budget * 0.8):
                completed_quests.append(102)
                points_to_add += quests[1]["points"]
        else:
             budgets_cursor = db.budgets.find({"user_id": user_id, "month": current_month, "year": current_year})
             budgets = await budgets_cursor.to_list(length=100)
             cat_budget_sum = sum(b["limit"] for b in budgets)
             
             if cat_budget_sum > 0 and total_spent > 0 and total_spent <= (cat_budget_sum * 0.8):
                 completed_quests.append(102)
                 points_to_add += quests[1]["points"]

    if 103 not in completed_quests:
        cat_count = await db.expenses.count_documents({
            "user_id": user_id, 
            "category": {"$ne": "Uncategorized"}
        })
        if cat_count >= 5:
            completed_quests.append(103)
            points_to_add += quests[2]["points"]
            
    if points_to_add > 0:
        await db.users.update_one(
            {"_id": user_oid},
            {
                "$set": {"completed_quests": completed_quests},
                "$inc": {"points": points_to_add}
            }
        )
        current_points += points_to_add

    ui_quests = []
    for q in quests:
        q_copy = q.copy()
        q_copy["completed"] = q["id"] in completed_quests
        ui_quests.append(q_copy)
        
    return ui_quests, current_points
