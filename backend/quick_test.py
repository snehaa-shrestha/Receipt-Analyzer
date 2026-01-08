import requests

print("Testing backend login endpoint...")

try:
    # Test with existing user
    response = requests.post(
        "http://localhost:8000/api/auth/login",
        json={"username": "user", "password": "user"},
        timeout=5
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\nSUCCESS - Login works!")
    else:
        print(f"\nFAILED - Error: {response.text}")
        
except Exception as e:
    print(f"ERROR: {e}")
