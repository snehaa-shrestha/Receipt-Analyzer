from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.get_database()
w = db.workspaces.find_one()
if w:
    print(f"Workspace: {w.get('name')}")
    print(f"Members: {w.get('members')}")
else:
    print("No workspaces in DB")

u = db.users.find_one({"username": "tester_jetski_123"})
if u:
    print(f"User ID: {u['_id']} (type: {type(u['_id'])})")
else:
    print("User not found")
