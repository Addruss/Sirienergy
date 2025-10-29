# Test Microservice 1 API Documentation

## Overview
This is a simple test microservice for the Sirienergy platform that provides a basic HTTP endpoint.

## Base URL
```
https://sirienergy.uab.cat/test_ms1
```

## Endpoints

### GET /test_ms1
Returns a test message from the Sirienergy microservice.

#### Request
- **Method:** GET
- **Authentication:** None required
- **Parameters:** None

#### Response
**Success Response (200 OK)**
```json
{
    "message": "Test message from Sirienergy microservice"
}
```

## Configuration Details
- **Port:** 4999
- **Host:** 0.0.0.0 (accessible from any IP address)
- **Debug mode:** Enabled

## Example Usage

### Using curl
```bash
curl https://sirienergy.uab.cat/test_ms1
```

### Using Python requests
```python
import requests

response = requests.get('https://sirienergy.uab.cat/test_ms1')
print(response.json())
```

## Notes
- The service is deployed using Docker and runs behind an Nginx reverse proxy
- HTTPS is enforced through SSL/TLS certificates
- All HTTP traffic is automatically redirected to HTTPS