import requests
import json

BASE_URL = "http://localhost:8000/api/auth"

print("=" * 60)
print("TESTING AUTHENTICATION ENDPOINTS")
print("=" * 60)

# Test 1: Register a new user
print("\n1. Testing REGISTER endpoint...")
register_data = {
    "username": "testuser999",
    "email": "testuser999@test.com",
    "password": "password123",
    "full_name": "Test User"
}

try:
    response = requests.post(f"{BASE_URL}/register", json=register_data, timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ REGISTER SUCCESS: {response.json()}")
    else:
        print(f"   ✗ REGISTER FAILED: {response.text}")
except Exception as e:
    print(f"   ✗ REQUEST ERROR: {e}")

# Test 2: Login with the user
print("\n2. Testing LOGIN endpoint...")
login_data = {
    "username": "testuser999",
    "password": "password123"
}

try:
    response = requests.post(f"{BASE_URL}/login", json=login_data, timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ LOGIN SUCCESS!")
        print(f"   Token: {data.get('access_token', '')[:50]}...")
        print(f"   Username: {data.get('username')}")
    else:
        print(f"   ✗ LOGIN FAILED: {response.text}")
except Exception as e:
    print(f"   ✗ REQUEST ERROR: {e}")

# Test 3: Login with existing user
print("\n3. Testing LOGIN with existing user 'user'...")
login_data2 = {
    "username": "user",
    "password": "user"
}

try:
    response = requests.post(f"{BASE_URL}/login", json=login_data2, timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ LOGIN SUCCESS!")
        print(f"   Token: {data.get('access_token', '')[:50]}...")
    else:
        print(f"   ✗ LOGIN FAILED: {response.text}")
except Exception as e:
    print(f"   ✗ REQUEST ERROR: {e}")

print("\n" + "=" * 60)
print("TESTS COMPLETE")
print("=" * 60)
