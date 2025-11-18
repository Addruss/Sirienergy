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

def test_pvlib_generation():
    """Retrieve PV generation data for authenticated user."""
    cookie = load_cookie()
    if not cookie:
        return

    session = requests.Session()
    session.cookies.set("user_data", cookie)

    print("=== Testing PVLib Generation Endpoint ===\n")

    try:
        r = session.get(
            f"{BASE_URL}/processing/pvlibGen",
            verify=VERIFY_SSL,
            timeout=30
        )
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            response_data = r.json()
            user_data = response_data.get('user', {})
            power_array = response_data.get('power', [])
            
            print(f"\n=== User Data ===")
            print(f"Latitude: {user_data.get('latitude')}")
            print(f"Longitude: {user_data.get('longitude')}")
            print(f"Altitude: {user_data.get('altitude')} m")
            print(f"Surface: {user_data.get('surface')} m²")
            print(f"Efficiency: {user_data.get('efficiency')}%")
            print(f"Timezone: {user_data.get('timezone')}")
            
            print(f"\n=== Power Generation Data ===")
            print(f"Total data points: {len(power_array)}")
            
            if power_array:
                print(f"Min power: {min(power_array):.2f} W")
                print(f"Max power: {max(power_array):.2f} W")
                print(f"Average power: {sum(power_array)/len(power_array):.2f} W")
                
                print(f"\nFirst 10 power values (W):")
                for i, power in enumerate(power_array[:10]):
                    print(f"  Point {i+1}: {power:.2f}")
        else:
            print(f"Error Response: {json.dumps(r.json(), indent=2)}")

    except requests.exceptions.Timeout:
        print("❌ Request timeout - service may be slow or unreachable")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n✅ PVLib generation test completed")

if __name__ == "__main__":
    test_pvlib_generation()