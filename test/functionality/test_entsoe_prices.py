import requests
import os
import json

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

def test_entsoe_prices():
    """Retrieve day-ahead electricity prices for user's country."""
    cookie = load_cookie()
    if not cookie:
        return

    session = requests.Session()
    session.cookies.set("user_data", cookie)

    print("=== Testing ENTSO-E Prices Endpoint ===\n")

    # Retrieve ENTSO-E prices
    try:
        r = session.get(
            f"{BASE_URL}/entsoe/prices",
            verify=VERIFY_SSL,
            timeout=30
        )
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            response_data = r.json()
            print(f"\nUser: {response_data.get('user')}")
            print(f"Country: {response_data.get('country')}")
            print(f"\nPrice Data (first 5 points):")
            
            data = response_data.get('data', [])
            if isinstance(data, list):
                for i, point in enumerate(data[:5]):
                    print(f"  Point {i+1}: {json.dumps(point, indent=4)}")
                print(f"\nTotal data points retrieved: {len(data)}")
            else:
                print(json.dumps(data, indent=2))
        else:
            print(f"Error Response: {json.dumps(r.json(), indent=2)}")

    except requests.exceptions.Timeout:
        print("❌ Request timeout - ENTSO-E API may be slow or unreachable")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n✅ ENTSO-E prices test completed")

if __name__ == "__main__":
    test_entsoe_prices()