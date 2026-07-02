import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup_bad_expenses():
    """Remove expenses with unrealistic amounts (likely OCR errors)"""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.receipt_analyzer
    
    # Define a reasonable maximum amount (e.g., $1,000,000)
    MAX_REASONABLE_AMOUNT = 1000000
    
    print("=" * 80)
    print("CLEANING UP CORRUPTED EXPENSE DATA")
    print("=" * 80)
    
    # Find all expenses with amounts over the threshold
    bad_expenses = await db.expenses.find({
        "amount": {"$gt": MAX_REASONABLE_AMOUNT}
    }).to_list(length=1000)
    
    print(f"\nFound {len(bad_expenses)} expenses with amounts > ${MAX_REASONABLE_AMOUNT:,}")
    
    if bad_expenses:
        print("\nExpenses to be deleted:")
        for exp in bad_expenses:
            print(f"  - {exp.get('description', 'Unknown')}: ${exp.get('amount', 0):,.2f}")
            print(f"    User ID: {exp.get('user_id')}, Receipt ID: {exp.get('receipt_id', 'Manual')}")
        
        # Delete these expenses
        result = await db.expenses.delete_many({
            "amount": {"$gt": MAX_REASONABLE_AMOUNT}
        })
        print(f"\n✓ Deleted {result.deleted_count} corrupted expense records")
        
        # Also need to delete the associated receipts
        receipt_ids = [exp.get('receipt_id') for exp in bad_expenses if exp.get('receipt_id')]
        if receipt_ids:
            from bson import ObjectId
            receipt_oids = []
            for rid in receipt_ids:
                try:
                    receipt_oids.append(ObjectId(rid))
                except:
                    pass
            
            if receipt_oids:
                receipt_result = await db.receipts.delete_many({
                    "_id": {"$in": receipt_oids}
                })
                print(f"✓ Deleted {receipt_result.deleted_count} associated receipt records")
    else:
        print("\n✓ No corrupted expenses found!")
    
    # Summary after cleanup
    print("\n" + "=" * 80)
    print("SUMMARY AFTER CLEANUP")
    print("=" * 80)
    
    users = await db.users.find().to_list(length=100)
    for user in users:
        user_id = str(user["_id"])
        username = user.get("username", "Unknown")
        
        expenses = await db.expenses.find({"user_id": user_id}).to_list(length=10000)
        total = sum(float(e.get("amount") or 0) for e in expenses)
        
        print(f"\n{username}: {len(expenses)} expenses, Total: ${total:,.2f}")
    
    client.close()
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(cleanup_bad_expenses())
