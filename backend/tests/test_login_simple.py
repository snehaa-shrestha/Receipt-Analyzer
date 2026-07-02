import requests
import json

BASE_URL = "http://localhost:8000/api/auth"

print("=" * 60)
print("TESTING LOGIN WITH EXISTING USER")
print("=" * 60)

# Test with existing user from database
login_data = {
    "username": "user",
    "password": "user"
}

try:
    print(f"\nAttempting login to: {BASE_URL}/login")
    print(f"Credentials: {login_data}")
    
    response = requests.post(f"{BASE_URL}/login", json=login_data, timeout=10)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✓ LOGIN SUCCESSFUL!")
        data = response.json()
        print(f"Token received: {data.get('access_token', '')[:50]}...")
    else:
        print(f"\n✗ LOGIN FAILED")
        print(f"Error: {response.text}")
        
except requests.exceptions.Timeout:
    print("\n✗ REQUEST TIMED OUT - Server not responding")
except requests.exceptions.ConnectionError:
    print("\n✗ CONNECTION ERROR - Server not running")
except Exception as e:
    print(f"\n✗ ERROR: {e}")

print("\n" + "=" * 60)
