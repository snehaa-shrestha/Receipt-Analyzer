import requests
import time

BASE_URL = "http://localhost:8000/api"

def run_test():
    username = "user"
    password = "user"

    print("1. Login...")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=5)
        print(f"Login Status: {res.status_code}")
        if res.status_code != 200:
            print(f"Login Failed: {res.text}")
            return
        
        token = res.json()["access_token"]
        print("Token received")
        
        print("2. Get Profile (/users/me)...")
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/users/me", headers=headers, timeout=5)
        print(f"Profile Status: {res.status_code}")
        print(f"Profile Response: {res.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()
