from functools import wraps
from flask import request, jsonify, g, current_app
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Auth service URL
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:5001/api")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from headers or cookies
        token = request.headers.get("Authorization")
        current_app.logger.info("Attempting to extract token from headers")

        if not token:
            token = request.cookies.get("jwt")
            current_app.logger.info("Token not found in headers; checking cookies")

        if not token:
            current_app.logger.warning("Authorization token is missing")
            return jsonify({"error": "Authorization token is required"}), 401

        # Remove "Bearer " prefix if present
        token = token.replace("Bearer ", "")
        current_app.logger.debug(f"Token extracted: {token[:10]}... (truncated)")

        try:
            # Call the auth service to validate the token

            current_app.logger.info(
                "Calling auth service to validate token. The token is: " + token
            )
            response = requests.post(
                f"{AUTH_SERVICE_URL}/auth/validate-token",
                json={"token": token},
                timeout=5,  # Set a timeout to avoid hanging requests
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            current_app.logger.info("Auth service responded successfully")

            # Parse the response from the auth service
            user_data = response.json().get("user")
            if not user_data:
                current_app.logger.warning("Invalid token: No user data returned")
                return jsonify({"error": "Invalid token"}), 401

            # Store the user information in Flask's `g` context
            g.user = user_data
            current_app.logger.info(f"User authenticated: {user_data['id']}")
        except requests.exceptions.Timeout:
            current_app.logger.error("Auth service request timed out")
            return jsonify({"error": "Auth service timeout"}), 504
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Auth service error: {str(e)}")
            return jsonify({"error": f"Auth service error: {str(e)}"}), 500
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

        return f(*args, **kwargs)

    return decorated_function
