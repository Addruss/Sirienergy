import requests
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://sirienergy.uab.cat"

data = {
    "email": "example@uab.cat",
    "password": "123456"
}

session = requests.Session()

try:
    response = session.post(f"{BASE_URL}/user/login", json=data)
    print("Status:", response.status_code)
    print("Response:", response.text)
    response_json = response.json()
    print("JSON Response:", response_json)

    if "user_data" in session.cookies:
        print("✅ Cookie received and saved")
        cookie_path = os.path.join(SCRIPT_DIR, "cookies.txt")
        with open(cookie_path, "w") as f:
            f.write(session.cookies.get_dict()["user_data"])
        print(f"Cookie saved to: {cookie_path}")
    else:
        print("⚠️ No cookie returned")
        print(f"Available cookies: {dict(session.cookies)}")
except requests.RequestException as e:
    print("❌ Request failed:", e)
except ValueError as e:
    print("❌ JSON parsing error:", e)