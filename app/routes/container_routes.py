import jwt
import datetime
import docker
from flask import Blueprint, request, jsonify, make_response, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.container import Container, ContainerStatus
from app.models.available_models import AvailableModel
from app import db
from dotenv import load_dotenv
import os
from app.middleware.protected import login_required

# Load variables from .env file
load_dotenv()

# Define the Blueprint
deploy_bp = Blueprint("deploy", __name__, url_prefix="/api/deploy")

# Secret key for signing tokens (should be stored in environment variables in production)
SECRET_KEY = os.environ.get("SECRET_KEY")  # Replace with an environment variable


@deploy_bp.route("/container", methods=["POST"])
@login_required
def make_container():
    current_app.logger.info("Make container endpoint hit")

    # Parse request data
    user = g.get("user", None)
    if not user:
        current_app.logger.warning("Unauthorized access attempt: No user in context")
        return jsonify({"error": "User not authenticated"}), 401

    data = request.get_json()
    available_model_id = data.get("available_model_id")
    env_vars = data.get("environment", {})  # Default to an empty object

    current_app.logger.debug(f"Request data received: {data}")

    # Validate required fields
    if not available_model_id:
        current_app.logger.warning("Request missing 'available_model_id'")
        return make_response(
            jsonify({"error": "Missing required field: 'available_model_id'"}), 400
        )

    # Fetch the available model
    available_model = AvailableModel.query.get(available_model_id)
    if not available_model:
        current_app.logger.warning(
            f"Available model with ID {available_model_id} not found"
        )
        return make_response(
            jsonify(
                {"error": f"Available model with ID {available_model_id} not found"}
            ),
            404,
        )

    current_app.logger.info(f"Available model found: {available_model.name}")

    # Create a Docker client
    client = docker.from_env()

    try:
        current_app.logger.info(
            f"Attempting to run Docker container for image {available_model.docker_image}"
        )
        # Run a container
        container = client.containers.run(
            image=available_model.docker_image,
            detach=True,  # Run in the background
            environment=env_vars,  # Pass environment variables
        )

        current_app.logger.info(f"Container {container.id} started successfully")

        # Add container to the database
        new_container = Container(
            user_id=user["id"],  # Example user_id
            available_model_id=available_model_id,
            status=ContainerStatus.RUNNING,
            config={"environment": env_vars},
        )
        db.session.add(new_container)
        db.session.commit()

        current_app.logger.info(
            f"Container {container.id} added to the database for user {user['id']}"
        )

        return jsonify(
            {
                "message": "Container created successfully",
                "container_id": container.id,
                "available_model_id": available_model_id,
                "environment": env_vars,
            }
        )
    except docker.errors.ImageNotFound:
        current_app.logger.error(
            f"Docker image {available_model.docker_image} not found"
        )
        return make_response(
            jsonify({"error": f"Image {available_model.docker_image} not found"}), 404
        )
    except docker.errors.APIError as e:
        current_app.logger.error(f"Docker API error: {str(e)}")
        return make_response(jsonify({"error": "Docker API error"}), 500)
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return make_response(jsonify({"error": "Internal server error"}), 500)
