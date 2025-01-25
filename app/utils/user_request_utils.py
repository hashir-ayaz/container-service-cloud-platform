import hashlib
import socket
import docker


# this function hashes the user_id and returns a port number
def hash_to_port(user_id, base_port=6000, port_range=1000):
    hash_object = hashlib.sha256(str(user_id).encode())
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


def assign_port(user_id, max_retries=10):
    base_port = hash_to_port(user_id)
    port = base_port

    for _ in range(max_retries):
        if is_port_available(port):
            return port
        port += 1

    raise Exception("No available port found after retries")
