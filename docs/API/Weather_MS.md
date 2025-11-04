# Weather Microservice API Documentation

## Overview
The Weather Microservice provides weather forecasting data and visual representations for specified locations. It uses Open-Meteo API for weather forecasts and WeatherAPI for astronomical data.

## Base URL
```
https://sirienergy.uab.cat/weather_ms
```

## Endpoints

### GET /weather
Returns a list of weather images based on the user's location data stored in cookies.

#### Request
- **Method:** GET
- **Authentication:** Required (via user_data cookie)
- **Parameters:** None (uses location data from cookie)
- **Required Cookie:** `user_data` (contains encrypted location information)

#### Response

**Success Response (200 OK)**
```json
{
    "weather_images": [
        "day-100",
        "day-200",
        "night-300",
        // ... 24 hour forecast
    ]
}
```

**Error Responses**

*Authentication Error (401)*
```json
{
    "error": "Authentication required"
}
```

*Invalid Parameters (400)*
```json
{
    "error": "Invalid coordinate values: [error message]"
}
```

*Server Error (500)*
```json
{
    "error": "Weather data retrieval failed: [error message]"
}
```

## Configuration Details
- **Port:** 5002
- **Host:** 0.0.0.0
- **Required Environment Variables:**
  - `WEATHER_API_API_KEY`: API key for WeatherAPI service
  - `SECRET_KEY`: Secret key for cookie encryption

## Example Usage

### Using Python requests
```python
import requests

cookies = {'user_data': 'encrypted_user_data'}
response = requests.get('https://sirienergy.uab.cat/weather_ms/weather', cookies=cookies)
print(response.json())
```

## Notes
- Returns 24-hour weather forecast data
- Weather images are named in format: "[day/night]-[weather_code]"
- Cookie must contain encrypted latitude, longitude, and timezone data
- Uses caching for weather API requests (1-hour expiration)
- Implements retry mechanism for API requests