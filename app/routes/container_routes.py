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
from app.utils.user_request_utils import assign_port

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
    print(f"Auth service url is {os.environ.get('AUTH_SERVICE_URL')}")

    # Parse request data
    user = g.get("user", None)
    if not user:
        current_app.logger.warning("Unauthorized access attempt: No user in context")
        return jsonify({"error": "User not authenticated"}), 401

    data = request.get_json()
    available_model_id = data.get("available_model_id")
    env_vars = data.get("environment", {})  # Default to an empty object
    name = data.get("name")
    requested_ports = data.get("ports", [])  # Ports requested by the user

    current_app.logger.debug(f"Request data received: {data}")

    # Validate required fields
    if not available_model_id:
        current_app.logger.warning("Request missing 'available_model_id'")
        return make_response(
            jsonify({"error": "Missing required field: 'available_model_id'"}), 400
        )

    if not requested_ports:
        current_app.logger.warning("Request missing 'ports'")
        return make_response(jsonify({"error": "Missing required field: 'ports'"}), 400)

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

    # Assign and validate ports
    try:
        host_ports = {}
        port_mappings = []  # To store the host-port to container-port mapping
        used_host_ports = set()  # To track already used host ports

        for i, port_entry in enumerate(requested_ports):
            container_port = port_entry.get("port")
            protocol = port_entry.get(
                "protocol", "tcp"
            )  # Default to TCP if not provided

            if not container_port:
                current_app.logger.warning(f"Port entry missing 'port': {port_entry}")
                continue

            for _ in range(25):  # Retry up to 25 times for a unique host port
                host_port = assign_port(user["id"], unique_offset=i)
                if host_port not in used_host_ports:
                    used_host_ports.add(host_port)
                    break
            else:
                raise Exception("Failed to find a unique host port after retries")

            host_ports[f"{container_port}/{protocol}"] = host_port
            port_mappings.append(
                {
                    "host_port": host_port,
                    "container_port": container_port,
                    "protocol": protocol,
                }
            )

        current_app.logger.info(f"Assigned port mappings: {port_mappings}")
    except Exception as e:
        current_app.logger.error(f"Failed to assign ports: {str(e)}")
        return make_response(jsonify({"error": "Failed to assign ports"}), 500)

    # Create a Docker client
    client = docker.from_env()

    try:
        current_app.logger.info(
            f"Attempting to run Docker container for image {available_model.docker_image}"
        )
        # Run a container with the assigned ports
        container = client.containers.run(
            image=available_model.docker_image,
            detach=True,  # Run in the background
            environment=env_vars,  # Pass environment variables
            name=name,
            ports=host_ports,  # Map container ports to host ports
        )

        current_app.logger.info(
            f"Container {container.id} started successfully with ports {host_ports}"
        )

        # Add container to the database
        new_container = Container(
            user_id=user["id"],  # Example user_id
            available_model_id=available_model_id,
            status=ContainerStatus.RUNNING,
            config={"environment": env_vars},
            name=name,
            ports=port_mappings,  # Save the port mappings in the database
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
                "ports": port_mappings,  # Return the assigned ports in the response
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


@deploy_bp.route("/container/<string:container_id>", methods=["GET"])
@login_required
def get_container_by_id(container_id):
    current_app.logger.info(f"Fetching container with ID: {container_id}")

    container = Container.query.get(container_id)
    if not container:
        current_app.logger.warning(f"Container with ID {container_id} not found")
        return jsonify({"error": "Container not found"}), 404

    return jsonify(
        {
            "id": container.id,
            "user_id": container.user_id,
            "available_model_id": container.available_model_id,
            "status": container.status,
            "config": container.config,
            "created_at": container.created_at,
        }
    )


@deploy_bp.route("/containers/user/<int:user_id>", methods=["GET"])
@login_required
def get_containers_by_user_id(user_id):
    current_app.logger.info(f"Fetching containers for user ID: {user_id}")

    containers = Container.query.filter_by(user_id=user_id).all()
    if not containers:
        current_app.logger.warning(f"No containers found for user ID {user_id}")
        return jsonify({"error": "No containers found for the specified user"}), 404

    return jsonify(
        [
            {
                "id": container.id,
                "user_id": container.user_id,
                "available_model_id": container.available_model_id,
                "status": container.status,
                "config": container.config,
                "created_at": container.created_at,
            }
            for container in containers
        ]
    )
