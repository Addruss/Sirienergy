import requests
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://sirienergy.uab.cat"

session = requests.Session()

try:
    # First, load the cookie if it exists
    cookie_path = os.path.join(SCRIPT_DIR, "cookies.txt")
    if os.path.exists(cookie_path):
        with open(cookie_path, "r") as f:
            cookie_value = f.read().strip()
            session.cookies.set("user_data", cookie_value)
        print("✅ Cookie loaded from file")
    else:
        print("⚠️ No cookie file found")
        exit(1)

    # Make the request to /me endpoint
    response = session.get(f"{BASE_URL}/user/me")
    print("Status:", response.status_code)
    print("Response:", response.text)
    response_json = response.json()
    print("JSON Response:", response_json)

    if response.status_code == 200:
        print("✅ Successfully retrieved user data")
    else:
        print("❌ Failed to retrieve user data")

except requests.RequestException as e:
    print("❌ Request failed:", e)
except ValueError as e:
    print("❌ JSON parsing error:", e)
except Exception as e:
    print("❌ Unexpected error:", e)