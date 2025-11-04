from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer
import os

app = Flask(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
serializer = URLSafeSerializer(SECRET_KEY, salt="user-cookie")

@app.route("/test_ms2/location", methods=["GET"])
def get_location():
    cookie = request.cookies.get("user_data")
    if not cookie:
        return jsonify({"error": "No session cookie provided"}), 401

    try:
        data = serializer.loads(cookie)
        location = {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "altitude": data.get("altitude")
        }
        return jsonify(location)
    except Exception:
        return jsonify({"error": "Invalid or expired cookie"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4998, debug=True)
