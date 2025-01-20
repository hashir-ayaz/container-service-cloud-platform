import jwt
import datetime
import docker
from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.container import Container, ContainerStatus
from app import db
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

# Define the Blueprint
deploy_bp = Blueprint("deploy", __name__, url_prefix="/api/deploy")

# Secret key for signing tokens (should be stored in environment variables in production)
SECRET_KEY = os.environ.get("SECRET_KEY")  # Replace with an environment variable


@deploy_bp.route("/container", methods=["POST"])
def make_container(img_name):
    # Create a Docker client
    client = docker.from_env()

    # Run a container
    container = client.containers.run(
        "nginx",  # Image name
        detach=True,  # Run in the background
        ports={"80/tcp": 8082},  # Map container's port 80 to host port 8080
    )

    # TODO add container to db
    new_container = Container(
        status=ContainerStatus.RUNNING,
        image_name=img_name,
        config={"port": 8082},
    )

    print(f"Container {container.id} is running.")
    return jsonify({"container_id created ": container.id})
