import requests
import json

BASE_URL = "http://localhost:8000/api"

# Test with existing user
username = "user"  # From database
password = "user"  # Common test password

print(f"Testing login for user: {username}")
print(f"URL: {BASE_URL}/auth/login")

try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ LOGIN SUCCESSFUL!")
        print(f"Token: {data.get('access_token', 'N/A')[:50]}...")
    else:
        print(f"\n✗ LOGIN FAILED")
        try:
            error_data = response.json()
            print(f"Error Detail: {error_data.get('detail', 'No detail')}")
        except:
            print(f"Raw error: {response.text}")
            
except Exception as e:
    print(f"\n✗ REQUEST FAILED: {e}")
    import traceback
    traceback.print_exc()
