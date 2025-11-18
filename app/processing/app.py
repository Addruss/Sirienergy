import os
import logging
import requests

from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer

import pandas as pd
import pvlib
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")
REGISTER_SERVICE_URL = os.getenv("REGISTER_SERVICE_URL", "http://register:5003")

# Initialize serializer (same as user_ms)
serializer = URLSafeSerializer(app.config["SECRET_KEY"], salt="user-cookie")


def get_PV_gen(
    latitude: float,
    longitude: float,
    altitude: float,
    surface: float,
    efficiency: float,
    tz: str,
) -> list[float]:
    """Calculates photovoltaic (PV) power generation for a location and system.

    Args:
        latitude: Latitude of the location in degrees.
        longitude: Longitude of the location in degrees.
        altitude: Altitude of the location in meters.
        surface: Surface area of PV panels in square meters.
        efficiency: PV panel efficiency percentage (0-100).
        tz: Timezone of the location (e.g., 'Europe/Berlin').

    Returns:
        List of hourly PV power generation values in watts for September 21,
        2024.
    """
    location = pvlib.location.Location(
        latitude=latitude,
        longitude=longitude,
        tz=tz,
        altitude=altitude
    )

    times = pd.date_range(
        start=datetime(2024, 9, 21, 0),
        end=datetime(2024, 9, 21, 23, 59),
        freq='15min',
        tz=tz
    )

    clearsky = location.get_clearsky(times, model='ineichen')
    ghi = clearsky['ghi'].tolist()

    conversion_factor = (efficiency / 100) * surface
    return [irradiance * conversion_factor for irradiance in ghi]


def get_user_from_cookie(req):
    """Extract and validate user data from cookie."""
    cookie = req.cookies.get("user_data")
    if not cookie:
        return None, (jsonify({"error": "Authentication required"}), 401)

    try:
        data = serializer.loads(cookie)
        
        # Extract required fields
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
        altitude = float(data.get("altitude"))
        surface = float(data.get("surface"))
        efficiency = float(data.get("efficiency"))
        timezone = data.get("time_zone")
        
        if not all([latitude, longitude, altitude, surface, efficiency, timezone]):
            return None, (jsonify({"error": "Missing required user data in cookie"}), 400)
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "surface": surface,
            "efficiency": efficiency,
            "timezone": timezone
        }, None
    
    except ValueError as e:
        return None, (jsonify({"error": f"Invalid coordinate values: {str(e)}"}), 400)
    except Exception as e:
        return None, (jsonify({"error": f"Invalid cookie: {str(e)}"}), 401)


@app.route("/processing/pvlibGen", methods=["GET"])
def pvlib_production():
    """Calculates photovoltaic power generation for authenticated user.

    Gets location and system data from user_data cookie.

    Returns:
        JSON response with power values or error message:
        - 401 for missing/invalid cookie
        - 400 for missing user data
        - 500 for calculation errors
        - 200 with power data on success
    """
    user_data, err = get_user_from_cookie(request)
    if err:
        return err

    try:
        logging.info(
            "Processing PV generation request for coordinates: %f,%f",
            user_data["latitude"],
            user_data["longitude"]
        )
        
        power_array = get_PV_gen(
            latitude=user_data["latitude"],
            longitude=user_data["longitude"],
            altitude=user_data["altitude"],
            surface=user_data["surface"],
            efficiency=user_data["efficiency"],
            tz=user_data["timezone"]
        )

        logging.info("Generated power array with %d values", len(power_array))
        
        return jsonify({
            "user": user_data,
            "power": power_array
        }), 200

    except ValueError as error:
        logging.error(f"ValueError: {error}")
        return jsonify({"error": "Invalid parameter values"}), 400
    except Exception as error:
        logging.error(f"Exception: {error}")
        return jsonify({"error": str(error)}), 500


@app.route("/processing/surplus", methods=["POST"])
def calculate_surplus():
    """Calculates surplus from register microservice.
    
    Retrieves production and consumption data for a given day from the register
    microservice, then calculates surplus (production - consumption) hour by hour.
    
    Request body:
        day (str, optional): Date in ISO format (YYYY-MM-DD). Defaults to today.
    
    Returns:
        JSON response with surplus data or error message:
        - 401 for missing/invalid cookie
        - 400 for missing day parameter
        - 500 for register service errors
        - 200 with surplus data on success
    """
    user_email, err = get_user_from_cookie(request)
    if err:
        return err
    
    try:
        # Get the day from request body (default to today)
        body = request.get_json(silent=True) or {}
        day = body.get("day")
        
        if not day:
            return jsonify({"error": "Missing 'day' parameter"}), 400
        
        logging.info("Calculating surplus for day: %s", day)
        
        # Get production data from register microservice
        prod_response = requests.post(
            f"{REGISTER_SERVICE_URL}/register/get_production_day",
            json={"day": day},
            cookies=request.cookies,
            timeout=10
        )
        
        if prod_response.status_code != 200:
            logging.error("Failed to get production data: %s", prod_response.text)
            return jsonify({"error": "Failed to retrieve production data"}), 500
        
        production_data = prod_response.json().get("production", [])
        
        # Get consumption data from register microservice
        cons_response = requests.post(
            f"{REGISTER_SERVICE_URL}/register/get_consumption_day",
            json={"day": day},
            cookies=request.cookies,
            timeout=10
        )
        
        if cons_response.status_code != 200:
            logging.error("Failed to get consumption data: %s", cons_response.text)
            return jsonify({"error": "Failed to retrieve consumption data"}), 500
        
        consumption_data = cons_response.json().get("consumption", [])
        
        # Calculate surplus hour by hour
        surplus_data = []
        
        # Create dictionaries for quick lookup by hour
        prod_dict = {item["hour"]: item["value"] for item in production_data}
        cons_dict = {item["hour"]: item["value"] for item in consumption_data}
        
        # Get all unique hours
        all_hours = set(prod_dict.keys()) | set(cons_dict.keys())
        
        # Calculate surplus for each hour
        for hour in sorted(all_hours, key=lambda x: int(x)):
            production = prod_dict.get(hour, 0)
            consumption = cons_dict.get(hour, 0)
            surplus = production - consumption
            
            surplus_data.append({
                "hour": hour,
                "production": production,
                "consumption": consumption,
                "surplus": surplus
            })
        
        logging.info("Calculated surplus for %d hours", len(surplus_data))
        
        return jsonify({
            "day": day,
            "surplus": surplus_data
        }), 200

    except requests.exceptions.Timeout:
        logging.error("Timeout connecting to register service")
        return jsonify({"error": "Register service timeout"}), 500
    except requests.exceptions.ConnectionError as e:
        logging.error("Connection error: %s", str(e))
        return jsonify({"error": "Failed to connect to register service"}), 500
    except Exception as error:
        logging.error(f"Exception: {error}")
        return jsonify({"error": str(error)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)