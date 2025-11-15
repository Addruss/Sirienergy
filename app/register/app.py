import os
import redis
import json
from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer
from datetime import datetime, timezone

app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Initialize serializer and Redis
serializer = URLSafeSerializer(app.config["SECRET_KEY"], salt="user-cookie")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class RedisModel:
    """A model for managing user data in Redis."""

    def __init__(self, redis_conn):
        self.redis = redis_conn

    def get_user_email_from_cookie(self, cookie_value):
        """Deserialize cookie and extract user email."""
        try:
            data = serializer.loads(cookie_value)
            return data.get("email")
        except Exception as e:
            raise ValueError(f"Invalid cookie: {str(e)}")

    def create_user_if_not_exists(self, user_email: str) -> dict:
        """Create user entry in Redis if it doesn't exist."""
        user_key = f"user:{user_email}"
        if not self.redis.exists(user_key):
            user_data = {
                "email": user_email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # store production/consumption as JSON strings
                "production": json.dumps({}),
                "consumption": json.dumps({}),
            }
            self.redis.hset(user_key, mapping=user_data)
        return self.get_user_data(user_email)

    def get_user_data(self, user_email: str) -> dict:
        """Retrieve user data from Redis."""
        user_key = f"user:{user_email}"
        data = self.redis.hgetall(user_key)
        if not data:
            return None

        # Parse JSON fields
        for key in ["production", "consumption"]:
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = json.loads(data[key])
                except json.JSONDecodeError:
                    data[key] = {}
        return data

    # Generic helpers for day/hour storage
    def _get_field(self, user_email: str, field: str) -> dict:
        user_key = f"user:{user_email}"
        raw = self.redis.hget(user_key, field)
        return json.loads(raw) if raw else {}

    def _save_field(self, user_email: str, field: str, payload: dict) -> None:
        user_key = f"user:{user_email}"
        self.redis.hset(user_key, field, json.dumps(payload))

    def add_entry(self, user_email: str, field: str, day: str, hour: str, value) -> None:
        """Add or update a single hour entry for a given day in the specified field."""
        payload = self._get_field(user_email, field)
        day = str(day)
        hour = str(hour)
        day_list = payload.get(day, [])
        # Replace existing hour entry if present
        replaced = False
        for item in day_list:
            if str(item.get("hour")) == hour:
                item["value"] = value
                replaced = True
                break
        if not replaced:
            day_list.append({"hour": hour, "value": value})
            # Optional: keep list ordered by hour
            try:
                day_list.sort(key=lambda x: int(x["hour"]))
            except Exception:
                pass
        payload[day] = day_list
        self._save_field(user_email, field, payload)

    def get_day(self, user_email: str, field: str, day: str) -> list:
        payload = self._get_field(user_email, field)
        return payload.get(str(day), [])


redis_model = RedisModel(redis_client)


def get_user_from_cookie(req):
    """Extract and validate user email from cookie."""
    cookie = req.cookies.get("user_data")
    if not cookie:
        return None, (jsonify({"error": "Authentication required"}), 401)

    try:
        user_email = redis_model.get_user_email_from_cookie(cookie)
        redis_model.create_user_if_not_exists(user_email)
        return user_email, None
    except Exception as e:
        return None, (jsonify({"error": str(e)}), 401)


def _current_day_iso():
    return datetime.now(timezone.utc).date().isoformat()


@app.route("/register/get_production_day", methods=["POST"])
def get_production_day():
    """Retrieve production data for authenticated user for a given day (or today)."""
    user_email, err = get_user_from_cookie(request)
    if err:
        return err

    try:
        body = request.get_json(silent=True) or {}
        day = body.get("day", _current_day_iso())
        data = redis_model.get_day(user_email, "production", day)
        return jsonify({"day": day, "production": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/register/set_production_day", methods=["POST"])
def set_production_day():
    """Save a single production entry (day + hour + value) for authenticated user."""
    user_email, err = get_user_from_cookie(request)
    if err:
        return err

    try:
        body = request.get_json() or {}
        day = body.get("day", _current_day_iso())
        hour = body.get("hour")
        value = body.get("value")
        if hour is None or value is None:
            return jsonify({"error": "Missing 'hour' or 'value' in payload"}), 400

        redis_model.add_entry(user_email, "production", day, hour, value)
        return jsonify({"status": "saved", "day": day, "hour": str(hour)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/register/get_consumption_day", methods=["POST"])
def get_consumption_day():
    """Retrieve consumption data for authenticated user for a given day (or today)."""
    user_email, err = get_user_from_cookie(request)
    if err:
        return err

    try:
        body = request.get_json(silent=True) or {}
        day = body.get("day", _current_day_iso())
        data = redis_model.get_day(user_email, "consumption", day)
        return jsonify({"day": day, "consumption": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/register/set_consumption_day", methods=["POST"])
def set_consumption_day():
    """Save a single consumption entry (day + hour + value) for authenticated user."""
    user_email, err = get_user_from_cookie(request)
    if err:
        return err

    try:
        body = request.get_json() or {}
        day = body.get("day", _current_day_iso())
        hour = body.get("hour")
        value = body.get("value")
        if hour is None or value is None:
            return jsonify({"error": "Missing 'hour' or 'value' in payload"}), 400

        redis_model.add_entry(user_email, "consumption", day, hour, value)
        return jsonify({"status": "saved", "day": day, "hour": str(hour)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003, debug=True)