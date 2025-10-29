import requests

def test_connection():
    url = "https://sirienergy.uab.cat/test_ms1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Connection successful!")
            print("Response:", response.json())
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
    except requests.exceptions.ConnectionError as error:
        print("❌ Connection failed. Error:", error)
    except Exception as error:
        print("❌ An unexpected error occurred:", error)

if __name__ == "__main__":
    test_connection()
