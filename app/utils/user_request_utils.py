import hashlib
import socket
import docker
import time  # Import time for the current timestamp
from app.models.container import Container


"""
- function to check if the user's container name is already taken by the user
- if it is taken, return true
- if it is not taken, return false
"""


def is_container_name_taken(container_name, user):
    users_containers = Container.query.filter_by(
        name=container_name, user_id=user.get("id")
    ).all()
    return len(users_containers) > 0


# This function hashes the user_id and the current time to return a port number
def hash_to_port(user_id, base_port=6000, port_range=1000):
    current_time = int(
        time.time()
    )  # Get the current time as an integer (seconds since epoch)
    unique_data = f"{user_id}_{current_time}"  # Combine user_id and current time
    hash_object = hashlib.sha256(unique_data.encode())
    hash_hex = hash_object.hexdigest()
    hash_int = int(hash_hex, 16)
    port = base_port + (hash_int % port_range)
    return port


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except socket.error:
            return False


def assign_port(user_id, unique_offset=0, max_retries=25):
    base_port = hash_to_port(user_id + unique_offset)
    port = base_port

    for _ in range(max_retries):
        if is_port_available(port):
            return port
        port += 1

    raise Exception("No available port found after retries")


def generate_subdomain(user_name, container_name):
    return f"{user_name}-{container_name}"
