import requests
import os
import json
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, "cookies.txt")
BASE_URL = "https://sirienergy.uab.cat"
VERIFY_SSL = True

def load_cookie():
    """Load cookie from file."""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            return f.read().strip()
    print("❌ No cookie file found. Run test_register.py first.")
    return None

def test_retrieve_data():
    """Retrieve production and consumption data for a specific day."""
    cookie = load_cookie()
    if not cookie:
        return

    session = requests.Session()
    session.cookies.set("user_data", cookie)

    today = datetime.now(timezone.utc).date().isoformat()

    print(f"Testing retrieve endpoints for {today}...\n")

    # Retrieve production data
    print("=== Retrieving Production Data ===")
    try:
        r = session.post(
            f"{BASE_URL}/register/get_production_day",
            json={"day": today},
            verify=VERIFY_SSL,
            timeout=10
        )
        print(f"Status: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}\n")
    except Exception as e:
        print(f"ERROR: {e}\n")

    # Retrieve consumption data
    print("=== Retrieving Consumption Data ===")
    try:
        r = session.post(
            f"{BASE_URL}/register/get_consumption_day",
            json={"day": today},
            verify=VERIFY_SSL,
            timeout=10
        )
        print(f"Status: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}\n")
    except Exception as e:
        print(f"ERROR: {e}\n")

    # Test with explicit day
    print("=== Testing with explicit day parameter ===")
    test_day = "2025-10-30"
    print(f"Requesting data for: {test_day}\n")
    
    try:
        r = session.post(
            f"{BASE_URL}/register/get_production_day",
            json={"day": test_day},
            verify=VERIFY_SSL,
            timeout=10
        )
        print(f"Production for {test_day}: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}\n")
    except Exception as e:
        print(f"ERROR: {e}\n")

    print("✅ Data retrieve test completed")

if __name__ == "__main__":
    test_retrieve_data()