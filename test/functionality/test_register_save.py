import requests
import os
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

def test_save_data():
    """Send production and consumption data hour by hour."""
    cookie = load_cookie()
    if not cookie:
        return

    session = requests.Session()
    session.cookies.set("user_data", cookie)

    today = datetime.now(timezone.utc).date().isoformat()
    
    # Test data: production and consumption for hours 0-5
    test_hours = [
        {"hour": "0", "value": 0.5},
        {"hour": "1", "value": 0.6},
        {"hour": "2", "value": 0.7},
        {"hour": "3", "value": 0.8},
        {"hour": "4", "value": 0.9},
        {"hour": "5", "value": 1.0},
    ]

    print(f"Testing save endpoints for {today}...\n")

    # Save production data
    print("=== Saving Production Data ===")
    for entry in test_hours:
        payload = {
            "day": today,
            "hour": entry["hour"],
            "value": entry["value"]
        }
        try:
            r = session.post(
                f"{BASE_URL}/register/set_production_day",
                json=payload,
                verify=VERIFY_SSL,
                timeout=10
            )
            print(f"Hour {entry['hour']}: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Hour {entry['hour']}: ERROR - {e}")

    print("\n=== Saving Consumption Data ===")
    for entry in test_hours:
        payload = {
            "day": today,
            "hour": entry["hour"],
            "value": entry["value"] * 0.8  # consumption slightly less
        }
        try:
            r = session.post(
                f"{BASE_URL}/register/set_consumption_day",
                json=payload,
                verify=VERIFY_SSL,
                timeout=10
            )
            print(f"Hour {entry['hour']}: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Hour {entry['hour']}: ERROR - {e}")

    print("\n✅ Data save test completed")

if __name__ == "__main__":
    test_save_data()