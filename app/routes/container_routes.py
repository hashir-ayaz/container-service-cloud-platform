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


def parse_request_data():
    data = request.get_json()
    available_model_id = data.get("available_model_id")
    env_vars = data.get("environment", {})
    name = data.get("name")
    requested_ports = data.get("ports", [])

    if not available_model_id:
        current_app.logger.warning("Request missing 'available_model_id'")
        raise ValueError("Missing required field: 'available_model_id'")
    if not requested_ports:
        current_app.logger.warning("Request missing 'ports'")
        raise ValueError("Missing required field: 'ports'")

    return available_model_id, env_vars, name, requested_ports


def fetch_available_model(available_model_id):
    available_model = AvailableModel.query.get(available_model_id)
    if not available_model:
        current_app.logger.warning(
            f"Available model with ID {available_model_id} not found"
        )
        raise LookupError(f"Available model with ID {available_model_id} not found")
    return available_model


def assign_ports(user_id, requested_ports):
    host_ports = {}
    port_mappings = []
    used_host_ports = set()

    for i, port_entry in enumerate(requested_ports):
        container_port = port_entry.get("port")
        protocol = port_entry.get("protocol", "tcp")

        if not container_port:
            current_app.logger.warning(f"Port entry missing 'port': {port_entry}")
            continue

        for _ in range(25):  # Retry up to 25 times for a unique host port
            host_port = assign_port(user_id, unique_offset=i)
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

    return host_ports, port_mappings


def run_docker_container(available_model, env_vars, name, host_ports):
    client = docker.from_env(timeout=200)
    try:
        container = client.containers.run(
            image=available_model.docker_image,
            detach=True,
            environment=env_vars,
            name=name,
            ports=host_ports,
        )
        return container
    except docker.errors.ImageNotFound:
        current_app.logger.error(
            f"Docker image {available_model.docker_image} not found"
        )
        raise LookupError(f"Image {available_model.docker_image} not found")
    except docker.errors.APIError as e:
        current_app.logger.error(f"Docker API error: {str(e)}")
        raise RuntimeError("Docker API error")


def save_container_to_db(user_id, available_model_id, name, env_vars, port_mappings):
    new_container = Container(
        user_id=user_id,
        available_model_id=available_model_id,
        status=ContainerStatus.RUNNING,
        config={"environment": env_vars},
        name=name,
        ports=port_mappings,
    )
    db.session.add(new_container)
    db.session.commit()
    return new_container


@deploy_bp.route("/container", methods=["POST"])
@login_required
def make_container():
    current_app.logger.info("Make container endpoint hit")

    user = g.get("user", None)
    if not user:
        current_app.logger.warning("Unauthorized access attempt: No user in context")
        return jsonify({"error": "User not authenticated"}), 401

    try:
        # Parse request data
        available_model_id, env_vars, name, requested_ports = parse_request_data()

        # Fetch the available model
        available_model = fetch_available_model(available_model_id)
        current_app.logger.info(f"Available model found: {available_model.name}")

        # Assign ports
        host_ports, port_mappings = assign_ports(user["id"], requested_ports)
        current_app.logger.info(f"Assigned port mappings: {port_mappings}")

        # Run Docker container
        container = run_docker_container(available_model, env_vars, name, host_ports)
        current_app.logger.info(f"Container {container.id} started successfully")

        # Save container to the database
        new_container = save_container_to_db(
            user_id=user["id"],
            available_model_id=available_model_id,
            name=name,
            env_vars=env_vars,
            port_mappings=port_mappings,
        )
        current_app.logger.info(f"Container {container.id} added to the database")

        return jsonify(
            {
                "message": "Container created successfully",
                "container_id": container.id,
                "available_model_id": available_model_id,
                "environment": env_vars,
                "ports": port_mappings,
            }
        )

    except ValueError as e:
        return make_response(jsonify({"error": str(e)}), 400)
    except LookupError as e:
        return make_response(jsonify({"error": str(e)}), 404)
    except RuntimeError as e:
        return make_response(jsonify({"error": str(e)}), 500)
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
                "name": container.name,
                "available_model_id": container.available_model_id,
                "model_name": container.available_model.name,  # Include model name
                "model_description": container.available_model.description,  # Include model description
                "docker_image": container.available_model.docker_image,  # Include Docker image
                "status": container.status.value,  # Convert Enum to string
                "ports": container.ports,  # Include port mappings
                "config": container.config,
                "created_at": container.created_at.isoformat(),  # Ensure JSON serializable
            }
            for container in containers
        ]
    )
