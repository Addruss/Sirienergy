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

def test_surplus_calculation():
    """Calculate surplus from production and consumption data."""
    cookie = load_cookie()
    if not cookie:
        return

    session = requests.Session()
    session.cookies.set("user_data", cookie)

    today = _current_day_iso()
    
    print("=== Testing Surplus Calculation Endpoint ===\n")

    try:
        payload = {"day": today}
        print(f"Requesting surplus calculation for day: {today}\n")
        
        r = session.post(
            f"{BASE_URL}/processing/surplus",
            json=payload,
            verify=VERIFY_SSL,
            timeout=30
        )
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            response_data = r.json()
            day = response_data.get("day")
            surplus_data = response_data.get("surplus", [])
            
            print(f"\n=== Surplus Data for {day} ===")
            print(f"Total hours with data: {len(surplus_data)}\n")
            
            if surplus_data:
                # Display all hours
                print("Hour | Production | Consumption | Surplus")
                print("-" * 50)
                for item in surplus_data:
                    hour = item["hour"]
                    prod = item["production"]
                    cons = item["consumption"]
                    surp = item["surplus"]
                    print(f"{hour:>4} | {prod:>10.2f} | {cons:>11.2f} | {surp:>7.2f}")
                
                # Calculate statistics
                total_production = sum(item["production"] for item in surplus_data)
                total_consumption = sum(item["consumption"] for item in surplus_data)
                total_surplus = sum(item["surplus"] for item in surplus_data)
                
                print("-" * 50)
                print(f"{'TOTAL':>4} | {total_production:>10.2f} | {total_consumption:>11.2f} | {total_surplus:>7.2f}")
                
                print(f"\n=== Statistics ===")
                print(f"Total Production: {total_production:.2f} W")
                print(f"Total Consumption: {total_consumption:.2f} W")
                print(f"Total Surplus: {total_surplus:.2f} W")
                
                avg_surplus = total_surplus / len(surplus_data) if surplus_data else 0
                print(f"Average Surplus per hour: {avg_surplus:.2f} W")
        else:
            print(f"Error Response: {json.dumps(r.json(), indent=2)}")

    except requests.exceptions.Timeout:
        print("❌ Request timeout - service may be slow or unreachable")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n✅ Surplus calculation test completed")

if __name__ == "__main__":
    test_surplus_calculation()