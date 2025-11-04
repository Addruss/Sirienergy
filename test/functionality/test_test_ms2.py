import os
import json
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, "cookies.txt")
BASE_URL = "https://sirienergy.uab.cat"

MODE = "register"  # or "login"
EMAIL = "example@uab.cat"
PASSWORD = "123456"

def save_cookie(session):
    v = session.cookies.get("user_data")
    if v:
        with open(COOKIE_FILE, "w") as f:
            f.write(v)

def load_cookie(session):
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            session.cookies.set("user_data", f.read().strip())
        return True
    return False

def do_register(session):
    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "country": "ES",
        "latitude": 41.4,
        "longitude": 2.1,
        "altitude": 10,
        "time_zone": "Europe/Madrid",
        "surface": 100,
        "efficiency": 0.18,
        "battery": True,
        "battery_energy_capacity": 5.0,
        "fee_type": "FIXED",
        "value": 0.12
    }
    r = session.post(f"{BASE_URL}/user/register", json=payload)
    print("register:", r.status_code, r.text)
    save_cookie(session)
    return r

def do_login(session):
    payload = {"email": EMAIL, "password": PASSWORD}
    r = session.post(f"{BASE_URL}/user/login", json=payload)
    print("login:", r.status_code, r.text)
    save_cookie(session)
    return r

def get_location(session):
    r = session.get(f"{BASE_URL}/test_ms2/location")
    print("location:", r.status_code)
    print("raw:", r.text)
    try:
        print("json:", json.dumps(r.json(), indent=2))
    except Exception as e:
        print("Error parsing JSON:", e)
    return r

def main():
    s = requests.Session()

    # prefer saved cookie unless you want to re-authenticate
    if not load_cookie(s):
        if MODE == "register":
            r = do_register(s)
        else:
            r = do_login(s)

        if r.status_code >= 400 and not s.cookies.get("user_data"):
            print("Auth failed, aborting")
            return

    get_location(s)

if __name__ == "__main__":
    main()