import jwt
import datetime
import docker
from flask import Blueprint, request, jsonify, make_response, g
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.container import Container, ContainerStatus
from app.models.available_model import AvailableModel
from app import db
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

# Define the Blueprint
deploy_bp = Blueprint("deploy", __name__, url_prefix="/api/deploy")

# Secret key for signing tokens (should be stored in environment variables in production)
SECRET_KEY = os.environ.get("SECRET_KEY")  # Replace with an environment variable


# Define the Blueprint
deploy_bp = Blueprint("deploy", __name__, url_prefix="/api/deploy")


@deploy_bp.route("/container", methods=["POST"])
@login_required
def make_container():
    # Parse request data
    user = g.get("user", None)
    data = request.get_json()
    available_model_id = data.get("available_model_id")
    env_vars = data.get("environment", {})  # Default to an empty object

    # Validate required fields
    if not available_model_id:
        return make_response(
            jsonify({"error": "Missing required field: 'available_model_id'"}), 400
        )

    # Fetch the available model
    available_model = AvailableModel.query.get(available_model_id)
    if not available_model:
        return make_response(
            jsonify(
                {"error": f"Available model with ID {available_model_id} not found"}
            ),
            404,
        )

    # Create a Docker client
    client = docker.from_env()

    try:
        # Run a container
        container = client.containers.run(
            image=available_model.docker_image,
            detach=True,  # Run in the background
            environment=env_vars,  # Pass environment variables
        )

        # Add container to the database
        new_container = Container(
            user_id=user.id,  # Example user_id
            available_model_id=available_model_id,
            status=ContainerStatus.RUNNING,
            config={"environment": env_vars},
        )
        db.session.add(new_container)
        db.session.commit()

        print(f"Container {container.id} is running.")
        return jsonify(
            {
                "message": "Container created successfully",
                "container_id": container.id,
                "available_model_id": available_model_id,
                "environment": env_vars,
            }
        )
    except docker.errors.DockerException as e:
        return make_response(jsonify({"error": str(e)}), 500)
