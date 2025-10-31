from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeSerializer
import os
import time

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
serializer = URLSafeSerializer(app.config["SECRET_KEY"], salt="user-cookie")


class User(db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(120), primary_key=True)
    password_hash = db.Column(db.String(200), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=False)
    time_zone = db.Column(db.String(50), nullable=False)
    surface = db.Column(db.Float, nullable=False)
    efficiency = db.Column(db.Float, nullable=False)
    battery = db.Column(db.Boolean, nullable=False)
    battery_energy_capacity = db.Column(db.Float, nullable=True)
    fee_type = db.Column(db.String(20), nullable=False)
    value = db.Column(db.Float, nullable=True)

def initialize_database():
    with app.app_context():
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                inspector = db.inspect(db.engine)
                if not inspector.has_table("users"):
                    db.create_all()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(retry_delay)

with app.app_context():
    app.before_request_funcs.setdefault(None, []).append(initialize_database)

def user_to_dict(user: User):
    """Convert DB user object to dict for cookie."""
    return {
        "email": user.email,
        "country": user.country,
        "latitude": user.latitude,
        "longitude": user.longitude,
        "altitude": user.altitude,
        "time_zone": user.time_zone,
        "surface": user.surface,
        "efficiency": user.efficiency,
        "battery": user.battery,
        "battery_energy_capacity": user.battery_energy_capacity,
        "fee_type": user.fee_type,
        "value": user.value,
    }


@app.route("/user/register", methods=["POST"])
def register():
    data = request.get_json()

    # Check required fields
    required = [
        "email", "password", "country", "latitude", "longitude", "altitude",
        "time_zone", "surface", "efficiency", "battery", "fee_type"
    ]
    for key in required:
        if key not in data:
            return jsonify({"error": f"Missing field {key}"}), 400

    if User.query.get(data["email"]):
        return jsonify({"error": "User already exists"}), 400

    if data["battery"] and "battery_energy_capacity" not in data:
        return jsonify({"error": "battery_energy_capacity required"}), 400
    if data["fee_type"] == "FIXED" and "value" not in data:
        return jsonify({"error": "value required when fee_type is FIXED"}), 400

    user = User(
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        country=data["country"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        altitude=data["altitude"],
        time_zone=data["time_zone"],
        surface=data["surface"],
        efficiency=data["efficiency"],
        battery=data["battery"],
        battery_energy_capacity=data.get("battery_energy_capacity"),
        fee_type=data["fee_type"],
        value=data.get("value"),
    )
    db.session.add(user)
    db.session.commit()

    cookie_data = user_to_dict(user)
    encoded = serializer.dumps(cookie_data)

    response = make_response(jsonify({"message": "User registered"}), 201)
    response.set_cookie("user_data", encoded, httponly=True)
    return response


@app.route("/user/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Missing credentials"}), 400
    
    user = User.query.get(data["email"])
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    cookie_data = user_to_dict(user)
    encoded = serializer.dumps(cookie_data)

    response = make_response(jsonify({"message": "Logged in"}))
    response.set_cookie("user_data", encoded, httponly=True)
    return response
    
@app.route("/user/me", methods=["GET"])
def me():
    cookie = request.cookies.get("user_data")
    if not cookie:
        return jsonify({"error": "No session"}), 401

    try:
        data = serializer.loads(cookie)
        return jsonify(data)
    except Exception:
        return jsonify({"error": "Invalid cookie"}), 401

@app.route("/user/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"message": "Logged out"}))
    resp.set_cookie("user_data", "", expires=0)
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
