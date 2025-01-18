import jwt
import datetime
from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User
from app import db

# Define the Blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Secret key for signing tokens (should be stored in environment variables in production)
SECRET_KEY = "yummysecret"  # Replace with an environment variable


def generate_token(user_id):
    """
    Generate a JWT token for the given user ID.
    """
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(hours=1),  # Token expiration
        "iat": datetime.datetime.utcnow(),  # Issued at
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# Login route
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        token = generate_token(user.id)

        # Set the JWT as a cookie
        response = make_response(jsonify({"message": "Login successful"}), 200)
        response.set_cookie("jwt", token, httponly=True, secure=True, samesite="Strict")
        return response

    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")

    if not email or not username or not password:
        return jsonify({"error": "Email, username, and password are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already exists"}), 409

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    new_user = User(email=email, username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    token = generate_token(new_user.id)

    response = make_response(
        jsonify({"message": f"User {username} registered successfully"}), 201
    )
    response.set_cookie("jwt", token, httponly=True, secure=True, samesite="Strict")
    return response


@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Logged out successfully"}), 200)
    response.set_cookie(
        "jwt", "", httponly=True, secure=True, samesite="Strict", expires=0
    )
    return response
