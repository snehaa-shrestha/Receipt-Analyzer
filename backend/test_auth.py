import os
import sys

# Add directory to path
sys.path.append(os.getcwd())

try:
    from app.utils.security import create_access_token, verify_password, get_password_hash
    print("Imports successful")
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

try:
    print("Testing Password Hash...")
    hashed = get_password_hash("testpassword")
    print(f"Hash created: {hashed}")
    
    print("Testing Password Verify...")
    is_valid = verify_password("testpassword", hashed)
    print(f"Password Valid: {is_valid}")
    
    print("Testing JWT Token Creation...")
    token = create_access_token(data={"sub": "testuser", "user_id": "12345"})
    print(f"Token created: {token}")
    
    print("ALL TESTS PASSED")
except Exception as e:
    print(f"RUNTIME ERROR: {e}")
    import traceback
    traceback.print_exc()
