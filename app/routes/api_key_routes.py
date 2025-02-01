import uuid
from flask import Blueprint, jsonify, request, current_app, g
from app import db
from app.models.api_key import APIKey
from app.models.container import Container
from app.middleware.protected import login_required
from werkzeug.security import generate_password_hash



# Define the Blueprint
api_key_bp = Blueprint("api_key", __name__, url_prefix="/api/api-keys")


# 🔹 Generate a secure API key
def generate_api_key():
    return str(uuid.uuid4()).replace("-", "")


# 🔹 Retrieve the authenticated user
def get_authenticated_user():
    user = g.get("user", None)
    if not user:
        current_app.logger.warning("Unauthorized access attempt: No user in context")
        return None
    return user


# 🔹 Fetch container and check if it belongs to the user
def get_user_container(container_id, user_id):
    container = Container.query.get(container_id)
    if not container:
        current_app.logger.warning(f"Container with ID {container_id} not found")
        return None, jsonify({"error": "Container not found"}), 404

    if container.user_id != user_id:
        current_app.logger.warning(
            f"Unauthorized attempt to access container {container_id}"
        )
        return None, jsonify({"error": "Unauthorized access to container"}), 403

    return container, None


# 🔹 Store a new API key in the database
def store_api_key(user_id, container_id):
    api_key_value = generate_api_key()
    current_app.logger.info(f"Generated API key: {api_key_value}")
    hashed_key = generate_password_hash(api_key_value)  # Hashing for security

    new_api_key = APIKey(
        user_id=user_id,
        container_id=container_id,
        key=hashed_key,
    )

    db.session.add(new_api_key)
    db.session.commit()

    current_app.logger.info(f"API key created for container {container_id} by user {user_id}")
    return api_key_value


# 🔹 Delete an API key from the database
def delete_api_key_by_id(api_key_id, user_id):
    api_key = APIKey.query.get(api_key_id)
    if not api_key:
        current_app.logger.warning(f"API Key with ID {api_key_id} not found")
        return jsonify({"error": "API Key not found"}), 404

    if api_key.user_id != user_id:
        current_app.logger.warning(f"Unauthorized attempt to delete API Key {api_key_id}")
        return jsonify({"error": "Unauthorized access to API Key"}), 403

    db.session.delete(api_key)
    db.session.commit()

    current_app.logger.info(f"API Key {api_key_id} deleted successfully by user {user_id}")
    return jsonify({"message": "API Key deleted successfully"}), 200


# 🔹 Create API Key Route
@api_key_bp.route("/create", methods=["POST"])
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
@api_key_bp.route("/delete/<string:api_key_id>", methods=["DELETE"])
@login_required
def delete_api_key(api_key_id):
    current_app.logger.info(f"Delete API Key endpoint hit for API key ID: {api_key_id}")

    # Retrieve authenticated user
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "User not authenticated"}), 401

    # Delete API key
    return delete_api_key_by_id(api_key_id, user["id"])

@api_key_bp.route("/<string:container_id>", methods=["GET"])
def get_api_keys_by_container_id(container_id):
    api_keys = APIKey.query.filter_by(container_id=container_id).all()
    
    if not api_keys:
        current_app.logger.warning(f"No API Keys found for container {container_id}")
        return jsonify({"error": "No API Keys found for container"}), 404
    
    current_app.logger.info(f"API Keys retrieved for container {container_id}: {api_keys}")
    return jsonify({"api_keys": [key.key for key in api_keys]}), 200

