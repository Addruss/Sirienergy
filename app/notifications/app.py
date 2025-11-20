import os
import logging
import requests
import json

from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer
from datetime import datetime, timezone

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
PROCESSING_SERVICE_URL = os.getenv("PROCESSING_SERVICE_URL", "http://processing:5005")

# Initialize serializer (same as user_ms)
serializer = URLSafeSerializer(app.config["SECRET_KEY"], salt="user-cookie")


def get_user_from_cookie(req):
    """Extract and validate user email from cookie."""
    cookie = req.cookies.get("user_data")
    if not cookie:
        return None, (jsonify({"error": "Authentication required"}), 401)

    try:
        data = serializer.loads(cookie)
        user_email = data.get("email")
        
        if not user_email:
            return None, (jsonify({"error": "Missing email in cookie"}), 401)
        
        return user_email, None
    except Exception as e:
        return None, (jsonify({"error": f"Invalid cookie: {str(e)}"}), 401)


def _current_day_iso():
    """Get current date in ISO format."""
    return datetime.now(timezone.utc).date().isoformat()


def complete_and_order_hours(data, default_value=0):
    """Completes and orders hourly data with default values for missing hours.
    
    Args:
        data (list): List of {"hour": str, "value": float} dicts.
        default_value: Default value for missing hours.
    
    Returns:
        dict: Ordered dictionary with all 24 hours in "HH:00" format.
    """
    all_hours = [f"{h:02d}:00" for h in range(24)]
    
    # Convert list to dict keyed by hour
    data_dict = {item["hour"]: item["value"] for item in data} if isinstance(data, list) else data
    
    completed_data = {hour: data_dict.get(hour, default_value) for hour in all_hours}
    return dict(sorted(completed_data.items()))


def hour_value_to_list(surplus_dict):
    """Converts hour-value dict to list of values in order."""
    return [surplus_dict[f"{h:02d}:00"] for h in range(24)]


@app.route("/notifications/consumption_peaks", methods=["POST"])
def get_consumption_peaks():
    """Detects consumption peaks by analyzing surplus data.
    
    Retrieves surplus data for a given day from the processing microservice.
    Calculates consumption mean and identifies hours where surplus is below
    the negative of the mean (indicating high consumption relative to production).
    
    Request body:
        day (str, optional): Date in ISO format (YYYY-MM-DD). Defaults to today.
    
    Returns:
        JSON response with peak hours or error message:
        - 401 for missing/invalid cookie
        - 400 for missing day parameter
        - 500 for processing service errors
        - 200 with peak hours data on success
    """
    user_email, err = get_user_from_cookie(request)
    if err:
        return err
    
    try:
        # Get the day from request body (default to today)
        body = request.get_json(silent=True) or {}
        day = body.get("day", _current_day_iso())
        
        logging.info("Detecting consumption peaks for user %s on %s", user_email, day)
        
        # Get surplus data from processing microservice
        surplus_response = requests.post(
            f"{PROCESSING_SERVICE_URL}/processing/surplus",
            json={"day": day},
            cookies=request.cookies,
            timeout=10
        )
        
        if surplus_response.status_code != 200:
            logging.error("Failed to get surplus data: %s", surplus_response.text)
            return jsonify({"error": "Failed to retrieve surplus data"}), 500
        
        surplus_data = surplus_response.json().get("surplus", [])
        
        # Extract consumption from surplus data
        # surplus = production - consumption, so consumption = production - surplus
        consumption_values = []
        for item in surplus_data:
            production = item.get("production", 0)
            surplus = item.get("surplus", 0)
            consumption = production - surplus
            consumption_values.append(consumption)
        
        # Calculate mean consumption
        if not consumption_values:
            return jsonify({"peak_hours": []}), 200
        
        consumption_mean = sum(consumption_values) / len(consumption_values)
        logging.info("Mean consumption: %f", consumption_mean)
        
        # Identify peak hours: where surplus is significantly negative
        # (consumption exceeds production by more than the average)
        peak_hours = []
        threshold = -1 * consumption_mean
        
        for item in surplus_data:
            hour = item.get("hour")
            surplus_value = item.get("surplus", 0)
            
            if surplus_value < threshold:
                peak_hours.append(hour)
                logging.debug("Peak detected at hour %s: surplus=%f (threshold=%f)", 
                            hour, surplus_value, threshold)
        
        logging.info("Detected %d peak hours for day %s", len(peak_hours), day)
        
        return jsonify({
            "day": day,
            "consumption_mean": consumption_mean,
            "threshold": threshold,
            "peak_hours": peak_hours
        }), 200

    except requests.exceptions.Timeout:
        logging.error("Timeout connecting to processing service")
        return jsonify({"error": "Processing service timeout"}), 500
    except requests.exceptions.ConnectionError as e:
        logging.error("Connection error: %s", str(e))
        return jsonify({"error": "Failed to connect to processing service"}), 500
    except Exception as error:
        logging.error(f"Exception: {error}")
        return jsonify({"error": str(error)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5006)