from functools import wraps
from flask import request, jsonify, g
import requests
import os

# Auth service URL
AUTH_SERVICE_URL = os.environ.get(
    "AUTH_SERVICE_URL", "http://localhost:5000/api/auth/validate-token"
)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "Authorization token is required"}), 401

        # Remove "Bearer " prefix if present
        token = token.replace("Bearer ", "")

        try:
            # Call the auth service to validate the token
            response = requests.post(
                AUTH_SERVICE_URL,
                json={"token": token},
                timeout=5,  # Set a timeout to avoid hanging requests
            )
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Parse the response from the auth service
            user_data = response.json().get("user")
            if not user_data:
                return jsonify({"error": "Invalid token"}), 401

            # Store the user information in Flask's `g` context
            g.user = user_data
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Auth service error: {str(e)}"}), 500

        return f(*args, **kwargs)

    return decorated_function
