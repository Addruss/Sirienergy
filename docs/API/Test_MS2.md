# Test Microservice 2 API Documentation

## Overview
This microservice exposes a single endpoint that returns a user's last-known location (latitude, longitude, altitude) based on a signed session cookie. It uses itsdangerous.URLSafeSerializer to deserialize and validate the cookie.

## Base URL
```
https://sirienergy.uab.cat/test_ms2
```
When running locally or in containerized deployments the app listens on 0.0.0.0:4998 by default.

## Configuration
- **SECRET_KEY:** Read from environment variable SECRET_KEY. Defaults to "default_secret_key" if not set.
- **Cookie serializer:** itsdangerous.URLSafeSerializer(SECRET_KEY, salt="user-cookie")
- **Host:** 0.0.0.0
- **Port:** 4998
- **Debug mode:** Enabled by default

## Endpoints

### GET /test_ms2/location
Returns the user's location extracted from a signed cookie.

#### Request
- **Method:** GET
- **Authentication:** Session cookie required
- **Cookie name:** "user_data"
- **Cookie signing:** Cookie must be a value previously created with URLSafeSerializer using the service SECRET_KEY and salt "user-cookie"
- **Parameters:** None (location data is read from the cookie)

#### Response
**Success Response (200 OK)**
```json
{
    "latitude": <number|null>,
    "longitude": <number|null>,
    "altitude": <number|null>
}
```
Each field will be present; values come from the deserialized cookie payload (may be null if not present).

**Error Responses**
- **401 Unauthorized**
```json
{"error": "No session cookie provided"}
```
Condition: The "user_data" cookie is missing.

- **400 Bad Request**
```json
{"error": "Invalid or expired cookie"}
```
Condition: The cookie could not be deserialized/validated.

## Example Usage

### Using curl
```bash
curl -v -H "Accept: application/json" --cookie "user_data=SIGNED_COOKIE_VALUE" \
  https://sirienergy.uab.cat/test_ms2/location
```

### Using Python requests
```python
import requests
cookies = {"user_data": "SIGNED_COOKIE_VALUE"}
resp = requests.get("https://sirienergy.uab.cat/test_ms2/location", cookies=cookies)
print(resp.status_code, resp.json())
```

## Notes
- Ensure HTTPS in production with Secure and HttpOnly cookie flags
- Cookie format and signing use itsdangerous.URLSafeSerializer with salt "user-cookie"
- Consider adding expiry handling and stricter payload validation
- Configure proxy headers and TLS termination when using reverse proxy Test Microservice 2 API Documentation

