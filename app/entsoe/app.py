import os
import logging

from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer

from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional
import requests
import xmltodict
import csv
import json

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

ENTSO_E_API_KEY = os.getenv('ENTSO_E_API_KEY')
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")

# Initialize serializer (same as user_ms)
serializer = URLSafeSerializer(app.config["SECRET_KEY"], salt="user-cookie")

def load_entsoe_country_keys() -> Dict[str, str]:
    """Loads country keys from a CSV file for ENTSO-E API queries.

    Returns:
        Dict[str, str]: A dictionary mapping country names to their respective 
            ENTSO-E keys.
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.abspath(
        os.path.join(base_dir, "tables/entsoe_country_keys.csv")
    )

    entsoe_country_keys: Dict[str, str] = {}
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            entsoe_country_keys[row["country"]] = row["key"]
    return entsoe_country_keys


def get_day_ahead_prices(
    country_name: str,
) -> Optional[List[Dict[str, Union[str, float]]]]:
    """Retrieves day-ahead electricity prices for a specified country.

    Args:
        country_name: The name of the country for which to retrieve prices.

    Returns:
        A list of price points for the day-ahead market, or None if the request
        fails.
    """

    endpoint = "https://web-api.tp.entsoe.eu/api"
    current_datetime = datetime.now()
    yesterday_datetime = current_datetime - timedelta(days=1)
    current_formatted = current_datetime.strftime("%Y%m%d") + "2200"
    yesterday_formatted = yesterday_datetime.strftime("%Y%m%d") + "2200"

    entsoe_country_keys = load_entsoe_country_keys()
    if country_name not in entsoe_country_keys:
        logging.error("Key for country %s not found", country_name)
        return None

    country_key = entsoe_country_keys[country_name]
    params = {
        "securityToken": ENTSO_E_API_KEY,
        "documentType": "A44",
        "in_Domain": country_key,
        "out_Domain": country_key,
        "periodStart": yesterday_formatted,
        "periodEnd": current_formatted,
    }

    response = requests.get(endpoint, params=params, timeout=30)
    data_xml = response.text
    data_dict = xmltodict.parse(data_xml)
    data_json = json.loads(json.dumps(data_dict))

    if response.status_code == 200:

        time_series_list = data_json["Publication_MarketDocument"].get(
            "TimeSeries", [])
        points = []

        if isinstance(time_series_list, list):
            for time_series in time_series_list:
                if time_series["Period"]["resolution"] == "PT15M":
                    points = time_series["Period"]["Point"]
                    break
        elif time_series_list["Period"]["resolution"] == "PT15M":
            points = time_series_list["Period"]["Point"]
        else:
            logging.info("Incorrect format: %s", time_series_list)

        return points
    else:
        logging.error(
            "Failed to retrieve data. Status code: %s, Response: %s",
            response.status_code,
            data_json,
        )
        return None


def get_user_from_cookie(req):
    """Extract and validate user email and country from cookie."""
    cookie = req.cookies.get("user_data")
    if not cookie:
        return None, None, (jsonify({"error": "Authentication required"}), 401)

    try:
        data = serializer.loads(cookie)
        user_email = data.get("email")
        country = data.get("country")
        
        if not user_email or not country:
            return None, None, (jsonify({"error": "Missing user data in cookie"}), 401)
        
        return user_email, country, None
    except Exception as e:
        return None, None, (jsonify({"error": f"Invalid cookie: {str(e)}"}), 401)


@app.route('/entsoe/prices', methods=['GET'])
def entsoe_prices():
    """Retrieves day-ahead electricity prices for the authenticated user's country.

    Gets country from user_data cookie.

    Returns:
        JSON response with prices data or error message:
        - 401 if cookie is missing/invalid
        - 500 if API request fails
        - 200 with prices data on success
    """
    user_email, country, err = get_user_from_cookie(request)
    if err:
        return err

    try:
        logging.info("Retrieving ENTSO-E prices for user %s in country %s", user_email, country)
        prices = get_day_ahead_prices(country)
        
        if prices is None:
            return jsonify({"error": "Failed to retrieve prices from ENTSO-E API"}), 500
        
        return jsonify({
            "user": user_email,
            "country": country,
            "data": prices
        }), 200
    except Exception as error:
        logging.error("Error retrieving ENTSO-E prices: %s", str(error))
        return jsonify({"error": str(error)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)