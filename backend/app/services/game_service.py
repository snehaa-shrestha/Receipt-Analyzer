from app.database import get_database
from datetime import datetime, timedelta
from bson import ObjectId

async def update_weekly_streak(user_id: str):
    db = get_database()
    try:
        user_oid = ObjectId(user_id)
    except:
        return

    user = await db.users.find_one({"_id": user_oid})
    if not user:
        return
        
    now = datetime.utcnow()
    year, week, _ = now.isocalendar()
    current_week_str = f"{year}-W{week:02d}"
    
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    receipt_count_this_week = await db.receipts.count_documents({
        "user_id": user_id,
        "uploaded_at": {"$gte": start_of_week}
    })
    
    if receipt_count_this_week < 2:
        return

    last_active_str = user.get("last_active_week")
    
    if not last_active_str:
        await db.users.update_one(
            {"_id": user_oid}, 
            {"$set": {"streak_count": 1, "last_active_week": current_week_str}}
        )
        return

    if last_active_str == current_week_str:
        return 

    prev_week_date = now - timedelta(days=7)
    prev_year, prev_week, _ = prev_week_date.isocalendar()
    expected_prev_str = f"{prev_year}-W{prev_week:02d}"

    if last_active_str == expected_prev_str:
        await db.users.update_one(
            {"_id": user_oid}, 
            {"$inc": {"streak_count": 1}, "$set": {"last_active_week": current_week_str}}
        )
    else:
        await db.users.update_one(
            {"_id": user_oid}, 
            {"$set": {"streak_count": 1, "last_active_week": current_week_str}}
        )

def get_display_streak(user: dict) -> int:
    last_active_str = user.get("last_active_week")
    streak_count = user.get("streak_count", 0)
    if not last_active_str or streak_count == 0:
        return 0
        
    now = datetime.utcnow()
    year, week, _ = now.isocalendar()
    current_week_str = f"{year}-W{week:02d}"
    
    prev_week_date = now - timedelta(days=7)
    prev_year, prev_week, _ = prev_week_date.isocalendar()
    prev_week_str = f"{prev_year}-W{prev_week:02d}"
    
    if last_active_str == current_week_str or last_active_str == prev_week_str:
        return streak_count
    
    return 0

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
        {"id": 101, "title": "Receipt Rookie", "description": "Upload your first receipt", "points": 50},
        {"id": 104, "title": "Receipt Regular", "description": "Upload 5 receipts", "points": 100},
        {"id": 105, "title": "Receipt Master", "description": "Upload 20 receipts", "points": 150},
        
        {"id": 103, "title": "Expense Explorer", "description": "Have 5 categorized expenses", "points": 50},
        {"id": 106, "title": "Categorization Pro", "description": "Have 15 categorized expenses", "points": 100},
        {"id": 107, "title": "Categorization Guru", "description": "Have 50 categorized expenses", "points": 150},
        
        {"id": 102, "title": "Budget Beginner", "description": "Spend less than 90% of your monthly budget", "points": 50},
        {"id": 108, "title": "Savvy Saver", "description": "Spend less than 75% of your monthly budget", "points": 100},
        {"id": 109, "title": "Frugal Master", "description": "Spend less than 50% of your monthly budget", "points": 150}
    ]
    
    points_to_add = 0
    newly_completed = []

    receipt_count = await db.receipts.count_documents({"user_id": user_id})
    cat_count = await db.expenses.count_documents({"user_id": user_id, "category": {"$ne": "Uncategorized"}})
    
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$gte": datetime(current_year, current_month, 1)}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    spent_result = await db.expenses.aggregate(pipeline).to_list(length=1)
    total_spent = spent_result[0]["total"] if spent_result else 0
    
    global_budget = user.get("monthly_budget", 0)
    if global_budget <= 0:
        budgets_cursor = db.budgets.find({"user_id": user_id, "month": current_month, "year": current_year})
        budgets = await budgets_cursor.to_list(length=100)
        global_budget = sum(b["limit"] for b in budgets)

    budget_ratio = (total_spent / global_budget) if global_budget > 0 else 1.0

    if 101 not in completed_quests and receipt_count >= 1:
        newly_completed.append(101)
    elif 101 in completed_quests and 104 not in completed_quests and receipt_count >= 5:
        newly_completed.append(104)
    elif 104 in completed_quests and 105 not in completed_quests and receipt_count >= 20:
        newly_completed.append(105)

    if 103 not in completed_quests and cat_count >= 5:
        newly_completed.append(103)
    elif 103 in completed_quests and 106 not in completed_quests and cat_count >= 15:
        newly_completed.append(106)
    elif 106 in completed_quests and 107 not in completed_quests and cat_count >= 50:
        newly_completed.append(107)
        
    if global_budget > 0 and total_spent > 0:
        if 102 not in completed_quests and budget_ratio <= 0.90:
            newly_completed.append(102)
        elif 102 in completed_quests and 108 not in completed_quests and budget_ratio <= 0.75:
            newly_completed.append(108)
        elif 108 in completed_quests and 109 not in completed_quests and budget_ratio <= 0.50:
            newly_completed.append(109)

    for q_id in newly_completed:
        completed_quests.append(q_id)
        q = next((q for q in quests if q["id"] == q_id), None)
        if q:
            points_to_add += q["points"]

    if points_to_add > 0:
        await db.users.update_one(
            {"_id": user_oid},
            {"$set": {"completed_quests": completed_quests}, "$inc": {"points": points_to_add}}
        )
        current_points += points_to_add

    ui_quests = []
    
    def add_next_uncompleted(chain_ids):
        for q_id in chain_ids:
            if q_id not in completed_quests:
                q = next((q for q in quests if q["id"] == q_id), None)
                if q:
                    ui_quests.append(q)
                break
                
    add_next_uncompleted([101, 104, 105])
    add_next_uncompleted([103, 106, 107])
    add_next_uncompleted([102, 108, 109])
        
    return ui_quests, current_points
