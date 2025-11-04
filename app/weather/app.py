import os
import logging

from flask import Flask, request, jsonify, render_template

from datetime import datetime
from typing import Tuple

import openmeteo_requests
import pandas as pd
import requests
import requests_cache
from retry_requests import retry

from itsdangerous import URLSafeSerializer

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

WEATHER_API_API_KEY = os.getenv('WEATHER_API_API_KEY')
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

serializer = URLSafeSerializer(SECRET_KEY, salt="user-cookie")


def get_weather(
    latitude: float,
    longitude: float,
    timezone: str,
) -> pd.DataFrame:
    """Retrieves hourly weather data for a location using Open-Meteo API.

    Args:
        latitude: Latitude of the location in degrees.
        longitude: Longitude of the location in degrees.
        timezone: Timezone of the location (e.g., 'Europe/Berlin').

    Returns:
        DataFrame containing hourly weather codes for the next 24 hours.
    """
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "weather_code",
        "timezone": timezone,
    }

    responses = openmeteo.weather_api("https://api.open-meteo.com/v1/forecast",
                                       params)
    response = responses[0]
    hourly = response.Hourly()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }

    utc_offset = pd.to_timedelta(response.UtcOffsetSeconds(), unit="s")
    hourly_data["date"] += utc_offset
    hourly_data["weather_code"] = hourly.Variables(0).ValuesAsNumpy()

    dataframe = pd.DataFrame(hourly_data).head(24)
    dataframe["weather_code"] = dataframe["weather_code"].astype(int).astype(str)
    return dataframe


def get_sunrise_sunset(latitude: float, longitude: float) -> Tuple[str, str]:
    """Retrieves sunrise and sunset times for a location using WeatherAPI.

    Args:
        latitude: Latitude of the location in degrees.
        longitude: Longitude of the location in degrees.

    Returns:
        Tuple containing sunrise and sunset times as strings ('06:30 AM' 
        format).

    Raises:
        requests.HTTPError: If API request fails.
    """
    url = "http://api.weatherapi.com/v1/astronomy.json"
    params = {
        "key": WEATHER_API_API_KEY,
        "q": f"{latitude},{longitude}",
        "aqi": "no",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    astronomy = data["astronomy"]["astro"]
    return astronomy["sunrise"], astronomy["sunset"]

def image_array(
    codes: pd.DataFrame,
    sunrise: str,
    sunset: str,
) -> list[str]:
    """Generates image names based on weather codes and day/night conditions.

    Args:
        codes: DataFrame containing weather codes and timestamps.
        sunrise: Sunrise time in 'HH:MM AM/PM' format.
        sunset: Sunset time in 'HH:MM AM/PM' format.

    Returns:
        List of image names in 'day-100' or 'night-200' format.

    Raises:
        ValueError: If any input is None.
    """
    if codes is None or sunrise is None or sunset is None:
        raise ValueError("All input parameters must be provided")

    codes["date"] = pd.to_datetime(codes["date"])
    sunrise_time = datetime.strptime(sunrise, "%I:%M %p").time()
    sunset_time = datetime.strptime(sunset, "%I:%M %p").time()

    def _get_day_night(timestamp: pd.Timestamp) -> str:
        """Determines if a timestamp is during daytime or nighttime."""
        time = timestamp.time()
        return "day" if sunrise_time <= time <= sunset_time else "night"

    codes["day_night"] = codes["date"].apply(_get_day_night)
    return codes.apply(
        lambda row: f"{row['day_night']}-{row['weather_code']}",
        axis=1
    ).tolist()

@app.route('/weather', methods=['GET'])
def weather():
    """Retrieves weather data and generates visual representation.

    Gets location data from user_data cookie.

    Returns:
        JSON response containing weather image list on success
        JSON error response with status code on failure:
        - 401 for missing/invalid cookie
        - 400 for invalid parameters
        - 500 for data retrieval failures
    """
    # Get and validate cookie
    cookie = request.cookies.get("user_data")
    if not cookie:
        return jsonify({
            'error': 'Authentication required'
        }), 401

    try:
        # Deserialize cookie data using the same serializer as user_ms
        data = serializer.loads(cookie)
        
        # Get required fields from cookie data
        latitude = float(data['latitude'])
        longitude = float(data['longitude']) 
        timezone = data['time_zone']

        logging.info("Processing weather request for coordinates: %f,%f", latitude, longitude)

        # Retrieve weather data
        weather_codes = get_weather(latitude, longitude, timezone)
        logging.info("Retrieved weather codes: %s", weather_codes)

        sunrise, sunset = get_sunrise_sunset(latitude, longitude)
        logging.info("Retrieved sunrise and sunset times: %s, %s", sunrise, sunset)

        image_list = image_array(weather_codes, sunrise, sunset)
        logging.info("Generated image list: %s", image_list)

        return jsonify({
            'weather_images': image_list
        })

    except ValueError as e:
        return jsonify({
            'error': f'Invalid coordinate values: {str(e)}'
        }), 400
    except Exception as e:
        logging.error("Weather data retrieval failed: %s", str(e))
        return jsonify({
            'error': f'Weather data retrieval failed: {str(e)}'
        }), 500
    
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)