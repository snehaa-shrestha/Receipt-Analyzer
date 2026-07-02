import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Redirect output to file
output_file = open("debug_tx_out.txt", "w", encoding="utf-8")
sys.stdout = output_file

async def debug_specific_tx():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.receipt_analyzer
    
    print("DEBUGGING SPECIFIC TRANSACTIONS")
    print("=" * 60)
    
    # Search for the transactions user mentioned
    keywords = ["BHAT", "Hankook", "om pw", "KSti"]
    
    for kw in keywords:
        query = {"description": {"$regex": kw, "$options": "i"}}
        txs = await db.expenses.find(query).to_list(length=100)
        
        for tx in txs:
            print(f"\nFound: {tx.get('description')}")
            print(f"  Amount: ${tx.get('amount')}")
            print(f"  Date: {tx.get('date')} (Type: {type(tx.get('date'))})")
            print(f"  Receipt ID: {tx.get('receipt_id')}")
            
    client.close()
    output_file.close()

if __name__ == "__main__":
    asyncio.run(debug_specific_tx())
