import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/auth"

def run_test():
    username = "debug_user_02"
    password = "password123"
    email = "debug02@example.com"
    
    print(f"Testing Auth Flow for {username}...")
    
    # 1. Register
    reg_data = {
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Debug User"
    }
    
    try:
        print("1. Attempting Register...")
        res = requests.post(f"{BASE_URL}/register", json=reg_data)
        print(f"Register Status: {res.status_code}")
        print(f"Register Response: {res.text}")
    except Exception as e:
        print(f"Register Failed: {e}")
        return

    # 2. Login
    login_data = {
        "username": username,
        "password": password
    }
    
    try:
        print("\n2. Attempting Login...")
        res = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"Login Status: {res.status_code}")
        print(f"Login Response: {res.text}")
        
    except Exception as e:
        print(f"Login Failed: {e}")

if __name__ == "__main__":
    try:
        run_test()
    except ImportError:
        print("Requests not installed, using urllib")
        # Fallback to urllib if requests is missing
        import urllib.request
        import urllib.error
        
        # ... logic for urllib implemented if needed, but requests is standard in this env usually
        # For brevity, assuming requests is there as it's a backend project
