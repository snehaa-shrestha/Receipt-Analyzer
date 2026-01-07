import asyncio
from app.database import get_database

async def audit_db():
    try:
        db = get_database()
        print("======== DATABASE AUDIT ========")
        
        # 1. Total Expenses
        total_docs = await db.expenses.count_documents({})
        pipeline_sum = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
        res = await db.expenses.aggregate(pipeline_sum).to_list(1)
        total_amount = res[0]['total'] if res else 0.0
        
        print(f"Total Expense Records: {total_docs}")
        print(f"Total Expenses Sum:    {total_amount:,.2f}")
        
        if total_docs == 0: 
            print("Database is empty.")
            return

        # 2. Group by Receipt
        print("\n--- Breakdown by Receipt ---")
        pipeline_receipt = [
            {"$group": {
                "_id": "$receipt_id", 
                "count": {"$sum": 1}, 
                "total": {"$sum": "$amount"}
            }}
        ]
        receipt_stats = await db.expenses.aggregate(pipeline_receipt).to_list(None)
        
        for stat in receipt_stats:
            rid = stat['_id']
            print(f"Receipt ID: {rid} | Items: {stat['count']} | Total: {stat['total']:,.2f}")
            
            # If this is the problematic receipt, list its items
            if stat['total'] > 10000:
                print(f"   !!! MALFORMED RECEIPT DETECTED ({stat['total']:,.2f}) !!!")
                print("   Listing aberrant items:")
                bad_items = await db.expenses.find({"receipt_id": rid}).sort("amount", -1).limit(10).to_list(None)
                for item in bad_items:
                    print(f"   - {item.get('description', '???')} : {item.get('amount', 0):,.2f}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(audit_db())
