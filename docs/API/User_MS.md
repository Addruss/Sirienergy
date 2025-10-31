# User Microservice API Documentation

## Overview
This microservice handles user management for the Sirienergy platform, including registration, authentication, and user profile management.

## Base URL
```
https://sirienergy.uab.cat/user
```

## Endpoints

### POST /user/register
Registers a new user in the system.

#### Request
- **Method:** POST
- **Content-Type:** application/json
- **Body:**
```json
{
    "email": "string",
    "password": "string",
    "country": "string",
    "latitude": float,
    "longitude": float,
    "altitude": float,
    "time_zone": "string",
    "surface": float,
    "efficiency": float,
    "battery": boolean,
    "battery_energy_capacity": float (required if battery is true),
    "fee_type": "string",
    "value": float (required if fee_type is "FIXED")
}
```

#### Response
**Success Response (201 Created)**
```json
{
    "message": "User registered"
}
```

**Error Response (400 Bad Request)**
```json
{
    "error": "Missing field {field_name}"
}
```
or
```json
{
    "error": "User already exists"
}
```

### POST /user/login
Authenticates a user and creates a session.

#### Request
- **Method:** POST
- **Content-Type:** application/json
- **Body:**
```json
{
    "email": "string",
    "password": "string"
}
```

#### Response
**Success Response (200 OK)**
```json
{
    "message": "Logged in"
}
```

**Error Response (401 Unauthorized)**
```json
{
    "error": "Invalid credentials"
}
```

### GET /user/me
Retrieves the current user's profile information.

#### Request
- **Method:** GET
- **Authentication:** Required (via httponly cookie)

#### Response
**Success Response (200 OK)**
```json
{
    "email": "string",
    "country": "string",
    "latitude": float,
    "longitude": float,
    "altitude": float,
    "time_zone": "string",
    "surface": float,
    "efficiency": float,
    "battery": boolean,
    "battery_energy_capacity": float,
    "fee_type": "string",
    "value": float
}
```

**Error Response (401 Unauthorized)**
```json
{
    "error": "No session"
}
```

### POST /user/logout
Ends the current user session.

#### Request
- **Method:** POST
- **Authentication:** Required (via httponly cookie)

#### Response
**Success Response (200 OK)**
```json
{
    "message": "Logged out"
}
```

## Authentication
The service uses httponly cookies for session management. Upon successful login or registration, a secure cookie named `user_data` is set.

## Notes
- The service uses SQLAlchemy with SQLite database (configurable via environment variables)
- Passwords are hashed using Werkzeug's security functions
- Session data is serialized using URLSafeSerializer
- The service runs on port 5001 in debug mode when run directly