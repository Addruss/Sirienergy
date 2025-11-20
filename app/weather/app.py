import json
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

import redis

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

WEATHER_API_API_KEY = os.getenv('WEATHER_API_API_KEY')
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

serializer = URLSafeSerializer(SECRET_KEY, salt="user-cookie")

REDIS_HOST = os.getenv("WEATHER_REDIS_HOST", os.getenv("REDIS_HOST", "weather_redis"))
REDIS_PORT = int(os.getenv("WEATHER_REDIS_PORT", os.getenv("REDIS_PORT", 6379)))
REDIS_DB = int(os.getenv("WEATHER_REDIS_DB", 0))
CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", 3600))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    redis_client.ping()
    logging.info("Connected to weather Redis %s:%d db=%d", REDIS_HOST, REDIS_PORT, REDIS_DB)
except Exception as e:
    logging.warning("Weather Redis unavailable (%s:%d db=%s): %s", REDIS_HOST, REDIS_PORT, REDIS_DB, e)
    redis_client = None

def get_weather(
    latitude: float,
    longitude: float,
    timezone: str,
) -> pd.DataFrame:
    """Retrieves hourly weather data for a location using Open-Meteo API.

    Uses a Redis cache (one hour by default) keyed by lat/lon/timezone/date to
    avoid repeated external API calls.
    """
    # use date in key so forecasts for different days are cached separately
    today = datetime.utcnow().date().isoformat()
    cache_key = f"weather:{latitude}:{longitude}:{timezone}:{today}"

    # try cache
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                logging.debug("Weather cache hit for %s", cache_key)
                cached_list = json.loads(cached)
                df = pd.DataFrame(cached_list)
                df["date"] = pd.to_datetime(df["date"])
                df["weather_code"] = df["weather_code"].astype(str)
                return df.head(24)
        except Exception as e:
            logging.warning("Weather Redis GET failed: %s", e)

    # existing behaviour: fetch from Open-Meteo
    cache_session = requests_cache.CachedSession(".cache", expire_after=CACHE_TTL_SECONDS)
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

    # save to redis cache
    if redis_client:
        try:
            serializable = dataframe.copy()
            serializable["date"] = serializable["date"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            redis_client.set(cache_key, json.dumps(serializable.to_dict(orient="records")), ex=CACHE_TTL_SECONDS)
            logging.debug("Cached weather under %s (ttl %ds)", cache_key, CACHE_TTL_SECONDS)
        except Exception as e:
            logging.warning("Weather Redis SET failed: %s", e)

    return dataframe

def get_sunrise_sunset(latitude: float, longitude: float) -> Tuple[str, str]:
    """Retrieves sunrise and sunset times for a location using WeatherAPI.

    Uses Redis cache (same TTL as weather) keyed by lat/lon/date to avoid extra API calls.
    """
    today = datetime.utcnow().date().isoformat()
    cache_key = f"sun:{latitude}:{longitude}:{today}"

    # Try cache
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                logging.debug("Sunrise/sunset cache hit for %s", cache_key)
                obj = json.loads(cached)
                return obj.get("sunrise"), obj.get("sunset")
        except Exception as e:
            logging.warning("Weather Redis GET failed for sunrise/sunset: %s", e)

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
    sunrise = astronomy["sunrise"]
    sunset = astronomy["sunset"]

    # Save to cache
    if redis_client:
        try:
            redis_client.set(cache_key, json.dumps({"sunrise": sunrise, "sunset": sunset}), ex=CACHE_TTL_SECONDS)
            logging.debug("Cached sunrise/sunset under %s (ttl %ds)", cache_key, CACHE_TTL_SECONDS)
        except Exception as e:
            logging.warning("Weather Redis SET failed for sunrise/sunset: %s", e)

    return sunrise, sunset

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