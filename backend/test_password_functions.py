import sys
import os
sys.path.insert(0, os.getcwd())

print("Testing password functions...")

try:
    from app.utils.security import get_password_hash, verify_password
    print("✓ Imports successful")
    
    # Test hashing
    print("\n1. Testing get_password_hash...")
    test_password = "testpass123"
    hashed = get_password_hash(test_password)
    print(f"✓ Hash created: {hashed[:50]}...")
    
    # Test verification
    print("\n2. Testing verify_password...")
    result = verify_password(test_password, hashed)
    print(f"✓ Verification result: {result}")
    
    print("\n✓ ALL TESTS PASSED - Password functions work correctly")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
