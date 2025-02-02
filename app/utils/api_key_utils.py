import uuid  # Generate unique API keys
from flask import current_app, g, jsonify  # Flask context and response handling
from werkzeug.security import generate_password_hash  # Securely hash API keys
from app import db  # Database instance
from app.models.api_key import APIKey  # API Key model
from app.models.container import Container  # Container model


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

    current_app.logger.info(
        f"API key created for container {container_id} by user {user_id}"
    )
    return api_key_value


# 🔹 Delete an API key from the database
def delete_api_key_by_id(api_key_id, user_id):
    api_key = APIKey.query.get(api_key_id)
    if not api_key:
        current_app.logger.warning(f"API Key with ID {api_key_id} not found")
        return jsonify({"error": "API Key not found"}), 404

    if api_key.user_id != user_id:
        current_app.logger.warning(
            f"Unauthorized attempt to delete API Key {api_key_id}"
        )
        return jsonify({"error": "Unauthorized access to API Key"}), 403

    db.session.delete(api_key)
    db.session.commit()

    current_app.logger.info(
        f"API Key {api_key_id} deleted successfully by user {user_id}"
    )
    return jsonify({"message": "API Key deleted successfully"}), 200
