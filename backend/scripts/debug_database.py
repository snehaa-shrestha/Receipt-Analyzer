import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Redirect output to file
output_file = open("debug_output.txt", "w", encoding="utf-8")
sys.stdout = output_file

async def debug_expenses():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.receipt_analyzer
    
    print("=" * 80)
    print("DEBUGGING EXPENSE CALCULATIONS")
    print("=" * 80)
    
    # Get all users
    users = await db.users.find().to_list(length=100)
    print(f"\nTotal Users: {len(users)}")
    
    for user in users:
        user_id = user["_id"]
        username = user.get("username", "Unknown")
        
        print(f"\n{'=' * 80}")
        print(f"USER: {username} (ID: {user_id})")
        print(f"Monthly Budget: {user.get('monthly_budget', 0)}")
        print(f"{'=' * 80}")
        
        # Check receipts
        receipts = await db.receipts.find({"user_id": str(user_id)}).to_list(length=1000)
        print(f"\nTotal Receipts: {len(receipts)}")
        
        receipt_total = 0
        for r in receipts:
            amount = r.get("total_amount") or 0
            receipt_total += float(amount)
            print(f"  - {r.get('merchant_name', 'Unknown')}: ${float(amount):,.2f} (Date: {r.get('date_extracted', 'N/A')})")
        
        print(f"\nTotal from Receipts Table: ${receipt_total:,.2f}")
        
        # Check expenses
        expenses = await db.expenses.find({"user_id": str(user_id)}).to_list(length=1000)
        print(f"\nTotal Expense Records: {len(expenses)}")
        
        manual_total = 0
        receipt_items_total = 0
        
        for e in expenses:
            amount = float(e.get("amount") or 0)
            if e.get("receipt_id"):
                receipt_items_total += amount
            else:
                manual_total += amount
                
        print(f"  - Manual Expenses Total: ${manual_total:,.2f}")
        print(f"  - Receipt Items Total: ${receipt_items_total:,.2f}")
        print(f"  - COMBINED Total: ${manual_total + receipt_items_total:,.2f}")
        
        # Show sample expenses
        print(f"\nSample Expenses (first 10):")
        for e in expenses[:10]:
            print(f"  - {e.get('description', 'N/A')}: ${e.get('amount', 0):,.2f} "
                  f"[Category: {e.get('category', 'N/A')}] "
                  f"[Receipt ID: {e.get('receipt_id', 'Manual')}]")
        
        # Check for anomalies
        print(f"\nChecking for anomalies...")
        large_expenses = [e for e in expenses if e.get("amount", 0) > 100000]
        if large_expenses:
            print(f"  ⚠️  Found {len(large_expenses)} expenses over $100,000:")
            for e in large_expenses:
                print(f"    - {e.get('description', 'N/A')}: ${e.get('amount', 0):,.2f}")
        else:
            print(f"  ✓ No anomalously large expenses found")
        
        # Category breakdown
        print(f"\nCategory Breakdown:")
        pipeline = [
            {"$match": {"user_id": str(user_id)}},
            {"$group": {"_id": "$category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]
        category_summary = await db.expenses.aggregate(pipeline).to_list(None)
        for cat in category_summary:
            print(f"  - {cat['_id']}: ${cat['total']:,.2f} ({cat['count']} items)")
    
    client.close()
    output_file.close()
    print("Debug output written to debug_output.txt", file=sys.__stdout__)

if __name__ == "__main__":
    asyncio.run(debug_expenses())
