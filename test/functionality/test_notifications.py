import requests
import os
import json
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, "cookies.txt")
BASE_URL = "https://sirienergy.uab.cat"
VERIFY_SSL = False

def load_cookie():
    """Load cookie from file."""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            return f.read().strip()
    print("❌ No cookie file found. Run test_register.py first.")
    return None

def _current_day_iso():
    """Get current date in ISO format."""
    return datetime.now(timezone.utc).date().isoformat()

def test_consumption_peaks():
    """Test consumption peaks detection."""
    cookie = load_cookie()
    if not cookie:
        return

    session = requests.Session()
    session.cookies.set("user_data", cookie)

    today = _current_day_iso()
    
    print("=== Testing Consumption Peaks Detection ===\n")

    try:
        payload = {"day": today}
        print(f"Requesting peak detection for day: {today}\n")
        
        r = session.post(
            f"{BASE_URL}/notifications/consumption_peaks",
            json=payload,
            verify=VERIFY_SSL,
            timeout=30
        )
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            response_data = r.json()
            
            print(f"\nDay: {response_data.get('day')}")
            print(f"Mean Consumption: {response_data.get('consumption_mean'):.2f} W")
            print(f"Peak Threshold: {response_data.get('threshold'):.2f} W")
            
            peak_hours = response_data.get("peak_hours", [])
            print(f"\nPeak Hours Detected: {len(peak_hours)}")
            if peak_hours:
                print("Peak hours:")
                for hour in peak_hours:
                    print(f"  - {hour}")
            else:
                print("No peak hours detected")
        else:
            print(f"Error Response: {json.dumps(r.json(), indent=2)}")

    except requests.exceptions.Timeout:
        print("❌ Request timeout - service may be slow or unreachable")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n✅ Consumption peaks test completed")

if __name__ == "__main__":
    test_consumption_peaks()