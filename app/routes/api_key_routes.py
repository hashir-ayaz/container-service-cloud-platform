import uuid
from flask import Blueprint, jsonify, request, current_app, g
from app import db
from app.models.api_key import APIKey
from app.models.container import Container
from app.middleware.protected import login_required
from werkzeug.security import generate_password_hash

# Define the Blueprint
api_key_bp = Blueprint("api_key", __name__, url_prefix="/api/api-keys")


@api_key_bp.route("/create", methods=["POST"])
@login_required
def create_api_key():
    current_app.logger.info("Create API Key endpoint hit")

    # Parse request data
    user = g.get("user", None)
    if not user:
        current_app.logger.warning("Unauthorized access attempt: No user in context")
        return jsonify({"error": "User not authenticated"}), 401

    data = request.get_json()
    container_id = data.get("container_id")

    # Validate required fields
    if not container_id:
        current_app.logger.warning("Request missing 'container_id'")
        return jsonify({"error": "Missing required field: 'container_id'"}), 400

    # Check if container exists and belongs to the user
    container = Container.query.get(container_id)
    if not container:
        current_app.logger.warning(f"Container with ID {container_id} not found")
        return jsonify({"error": "Container not found"}), 404

    if container.user_id != user["id"]:
        current_app.logger.warning(
            f"Unauthorized attempt to access container {container_id}"
        )
        return jsonify({"error": "Unauthorized access to container"}), 403

    # Generate a unique API key
    api_key_value = str(uuid.uuid4()).replace("-", "")

    # Create and store the API key in the database
    new_api_key = APIKey(
        user_id=user["id"],
        container_id=container_id,
        key=generate_password_hash(
            api_key_value
        ),  # Optionally hash the key for security
    )
    db.session.add(new_api_key)
    db.session.commit()

    current_app.logger.info(
        f"API key created for container {container_id} by user {user['id']}"
    )

    return (
        jsonify(
            {
                "message": "API key created successfully",
                "api_key": api_key_value,  # Return the plain key for the user to store
                "container_id": container_id,
            }
        ),
        201,
    )


@api_key_bp.route("/delete/<string:api_key_id>", methods=["DELETE"])
@login_required
def delete_api_key(api_key_id):
    current_app.logger.info(f"Delete API Key endpoint hit for API key ID: {api_key_id}")

    # Parse user from context
    user = g.get("user", None)
    if not user:
        current_app.logger.warning("Unauthorized access attempt: No user in context")
        return jsonify({"error": "User not authenticated"}), 401

    # Find the API key
    api_key = APIKey.query.get(api_key_id)
    if not api_key:
        current_app.logger.warning(f"API Key with ID {api_key_id} not found")
        return jsonify({"error": "API Key not found"}), 404

    # Ensure the API key belongs to the user
    if api_key.user_id != user["id"]:
        current_app.logger.warning(
            f"Unauthorized attempt to delete API Key {api_key_id}"
        )
        return jsonify({"error": "Unauthorized access to API Key"}), 403

    # Delete the API key
    db.session.delete(api_key)
    db.session.commit()

    current_app.logger.info(
        f"API Key {api_key_id} deleted successfully by user {user['id']}"
    )

    return jsonify({"message": "API Key deleted successfully"}), 200
