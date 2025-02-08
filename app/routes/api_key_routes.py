import uuid
from flask import Blueprint, jsonify, request, current_app, g
from app import db
from app.models.api_key import APIKey
from app.models.container import Container
from app.middleware.protected import login_required
from app.utils.api_key_utils import (
    delete_api_key_by_id,
    get_authenticated_user,
    get_user_container,
    store_api_key,
)
from app.utils.user_request_utils import extract_container_name

# Define the Blueprint
api_key_bp = Blueprint("api_key", __name__, url_prefix="/api/api-keys")


# 🔹 Create API Key Route
@api_key_bp.route("/", methods=["POST"])
@login_required
def create_api_key():
    current_app.logger.info("Create API Key endpoint hit")

    # Retrieve authenticated user
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "User not authenticated"}), 401

    data = request.get_json()
    container_id = data.get("container_id")

    if not container_id:
        current_app.logger.warning("Request missing 'container_id'")
        return jsonify({"error": "Missing required field: 'container_id'"}), 400

    # Validate container ownership
    container, error_response = get_user_container(container_id, user["id"])
    if error_response:
        return error_response

    # Generate and store API key
    api_key_value = store_api_key(user["id"], container_id)

    return (
        jsonify(
            {
                "message": "API key created successfully",
                "api_key": api_key_value,  # Return plain key for the user to store
                "container_id": container_id,
            }
        ),
        201,
    )


# 🔹 Delete API Key Route
@api_key_bp.route("/<string:api_key_id>", methods=["DELETE"])
@login_required
def delete_api_key(api_key_id):
    current_app.logger.info(f"Delete API Key endpoint hit for API key ID: {api_key_id}")

    # Retrieve authenticated user
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "User not authenticated"}), 401

    # Delete API key
    return delete_api_key_by_id(api_key_id, user["id"])


# 🔹 Get API Keys for a Container
@api_key_bp.route("/<string:container_id>", methods=["GET"])
@login_required
def get_api_keys_by_container_id(container_id):
    current_app.logger.info(f"Fetching API keys for container {container_id}")

    # Retrieve authenticated user
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "User not authenticated"}), 401

    # Validate container ownership
    container, error_response = get_user_container(container_id, user["id"])
    if error_response:
        return error_response

    # Fetch API keys for the container
    api_keys = APIKey.query.filter_by(container_id=container_id).all()

    if not api_keys:
        current_app.logger.warning(f"No API Keys found for container {container_id}")
        return jsonify({"error": "No API Keys found for container"}), 404

    return (
        jsonify(
            {
                "message": "API keys retrieved successfully",
                "container_id": container_id,  # Include container_id in response
                "api_keys": [
                    {
                        "id": key.id,
                        "key": key.key,
                        "container_id": key.container_id,  # Ensure each key has container_id
                    }
                    for key in api_keys
                ],
            }
        ),
        200,
    )


# Validate API Key
@api_key_bp.route("/validate", methods=["POST"])
def validate_api_key():
    """
    Validates the API key and ensures it has access to the requested container.
    """
    current_app.logger.info("Validate API Key endpoint hit")

    # 1️⃣ Check if API key is present in request headers
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"message": "Missing API Key"}), 400

    # 2️⃣ Check if API key exists in the database
    api_key_obj = APIKey.query.filter_by(key=api_key, is_active=True).first()
    if not api_key_obj:
        return jsonify({"message": "Invalid API Key"}), 401

    # 3️⃣ Extract container name from request URL
    host_url = request.host  # Example: "test-grafana-hashir.hashirayaz.site"
    container_name = extract_container_name(host_url)

    if not container_name:
        return jsonify({"message": "Invalid URL structure"}), 400

    # 4️⃣ Check if the API key is authorized to access this container
    container = Container.query.filter_by(
        id=api_key_obj.container_id, name=container_name
    ).first()

    if not container:
        return (
            jsonify({"message": "Forbidden: You don't have access to this container"}),
            403,
        )

    return jsonify({"message": "API Key validated successfully"}), 200
