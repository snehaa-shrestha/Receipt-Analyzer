from app.database import get_database
from datetime import datetime, timedelta
from bson import ObjectId

async def update_streak(user_id: str):
    db = get_database()
    try:
        user_oid = ObjectId(user_id)
    except:
        return

    user = await db.users.find_one({"_id": user_oid})
    if not user:
        return
        
    last_active = user.get("last_active_date")
    now = datetime.utcnow()
    today = now.date()
    
    if last_active:
        last_date = last_active.date()
        if today == last_date:
            return # Already active today
        elif today == last_date + timedelta(days=1):
            # Streak continues
            await db.users.update_one({"_id": user_oid}, {"$inc": {"streak_count": 1}, "$set": {"last_active_date": now}})
        else:
            # Streak broken
            if today > last_date:
                 await db.users.update_one({"_id": user_oid}, {"$set": {"streak_count": 1, "last_active_date": now}})
    else:
        # First time
        await db.users.update_one({"_id": user_oid}, {"$set": {"streak_count": 1, "last_active_date": now}})

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
    
    # 1. Receipt Rookie (Count >= 5)
    if 101 not in completed_quests:
        receipt_count = await db.receipts.count_documents({"user_id": user_id})
        if receipt_count >= 5:
            completed_quests.append(101)
            points_to_add += quests[0]["points"]

    # 2. Savvy Saver (< 80% Budget)
    if 102 not in completed_quests:
        current_month = datetime.utcnow().month
        current_year = datetime.utcnow().year
        
        # Get total spent this month
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "date": {"$gte": datetime(current_year, current_month, 1)}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        spent_result = await db.expenses.aggregate(pipeline).to_list(length=1)
        total_spent = spent_result[0]["total"] if spent_result else 0
        
        # Get total budget (User global budget or sum of categories)
        # Using global budget from user profile if set, else sum of cats
        global_budget = user.get("monthly_budget", 0)
        
        if global_budget > 0:
            if total_spent > 0 and total_spent <= (global_budget * 0.8):
                completed_quests.append(102)
                points_to_add += quests[1]["points"]
        else:
             # Fallback to sum of category budgets if no global
             budgets_cursor = db.budgets.find({"user_id": user_id, "month": current_month, "year": current_year})
             budgets = await budgets_cursor.to_list(length=100)
             cat_budget_sum = sum(b["limit"] for b in budgets)
             
             if cat_budget_sum > 0 and total_spent > 0 and total_spent <= (cat_budget_sum * 0.8):
                 completed_quests.append(102)
                 points_to_add += quests[1]["points"]

    # 3. Expense Explorer (5 categorized expenses)
    if 103 not in completed_quests:
        cat_count = await db.expenses.count_documents({
            "user_id": user_id, 
            "category": {"$ne": "Uncategorized"}
        })
        if cat_count >= 5:
            completed_quests.append(103)
            points_to_add += quests[2]["points"]
            
    # Apply updates if any
    if points_to_add > 0:
        await db.users.update_one(
            {"_id": user_oid},
            {
                "$set": {"completed_quests": completed_quests},
                "$inc": {"points": points_to_add}
            }
        )
        current_points += points_to_add

    # Return quest status for UI
    ui_quests = []
    for q in quests:
        q_copy = q.copy()
        q_copy["completed"] = q["id"] in completed_quests
        ui_quests.append(q_copy)
        
    return ui_quests, current_points
