import asyncio
import sys
import os
sys.path.append(os.getcwd())

async def test_login():
    from app.database import get_database
    from app.utils.security import verify_password, create_access_token
    
    db = get_database()
    
    # Check if any users exist
    users = await db.users.find({}).to_list(length=10)
    print(f"Found {len(users)} users in database")
    
    if users:
        for u in users:
            print(f"Username: {u.get('username')}, Email: {u.get('email')}")
    
    # Try to find a specific user
    test_user = await db.users.find_one({"username": "test"})
    if test_user:
        print(f"\nTest user found: {test_user.get('username')}")
        print(f"Password hash exists: {bool(test_user.get('password'))}")
        
        # Test password verification
        try:
            result = verify_password("test123", test_user["password"])
            print(f"Password 'test123' verification: {result}")
        except Exception as e:
            print(f"Password verification error: {e}")
            
        # Test token creation
        try:
            token = create_access_token(data={"sub": test_user["username"], "user_id": str(test_user["_id"])})
            print(f"Token created successfully: {token[:50]}...")
        except Exception as e:
            print(f"Token creation error: {e}")
    else:
        print("\nNo 'test' user found. Available usernames:")
        for u in users:
            print(f"  - {u.get('username')}")

if __name__ == "__main__":
    asyncio.run(test_login())
