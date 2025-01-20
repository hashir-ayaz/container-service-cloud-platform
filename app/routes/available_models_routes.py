from flask import Blueprint, request, jsonify, make_response
from app.models.available_model import AvailableModel
from app import db

# Define the Blueprint
model_bp = Blueprint("models", __name__, url_prefix="/api/models")


# CREATE: Add a new available model
@model_bp.route("/", methods=["POST"])
def create_model():
    data = request.get_json()

    # Validate required fields
    if not data or not data.get("name") or not data.get("docker_image"):
        return make_response(
            jsonify({"error": "Missing required fields: 'name' and 'docker_image'"}),
            400,
        )

    # Extract version and set default to "latest"
    version = data.get("version", "latest")

    # Check for duplicate name
    if AvailableModel.query.filter_by(name=data["name"]).first():
        return make_response(jsonify({"error": "Model name already exists"}), 400)

    # Check for duplicate docker_image and version (ignoring "latest")
    if (
        version != "latest"
        and AvailableModel.query.filter_by(
            docker_image=data["docker_image"], version=version
        ).first()
    ):
        return make_response(
            jsonify(
                {
                    "error": f"Docker image '{data['docker_image']}' with version '{version}' already exists"
                }
            ),
            400,
        )

    # Create and save the model
    new_model = AvailableModel(
        name=data["name"],
        description=data.get("description"),
        docker_image=data["docker_image"],
        version=version,
        is_active=data.get("is_active", True),
    )
    db.session.add(new_model)
    db.session.commit()

    return jsonify({"message": "Model created successfully", "model": new_model.name})


# READ: Get all available models
@model_bp.route("/", methods=["GET"])
def get_models():
    models = AvailableModel.query.all()
    return jsonify(
        [
            {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "docker_image": model.docker_image,
                "version": model.version,
                "is_active": model.is_active,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }
            for model in models
        ]
    )


# READ: Get a single model by ID
@model_bp.route("/<int:model_id>", methods=["GET"])
def get_model(model_id):
    model = AvailableModel.query.get(model_id)
    if not model:
        return make_response(jsonify({"error": "Model not found"}), 404)

    return jsonify(
        {
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "docker_image": model.docker_image,
            "version": model.version,
            "is_active": model.is_active,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
    )


# UPDATE: Update an existing model
@model_bp.route("/<int:model_id>", methods=["PUT"])
def update_model(model_id):
    model = AvailableModel.query.get(model_id)
    if not model:
        return make_response(jsonify({"error": "Model not found"}), 404)

    data = request.get_json()

    # Update fields if provided
    model.name = data.get("name", model.name)
    model.description = data.get("description", model.description)
    model.docker_image = data.get("docker_image", model.docker_image)
    model.version = data.get("version", model.version)
    model.is_active = data.get("is_active", model.is_active)

    db.session.commit()

    return jsonify({"message": "Model updated successfully", "model": model.name})


# DELETE: Delete a model
@model_bp.route("/<int:model_id>", methods=["DELETE"])
def delete_model(model_id):
    model = AvailableModel.query.get(model_id)
    if not model:
        return make_response(jsonify({"error": "Model not found"}), 404)

    db.session.delete(model)
    db.session.commit()

    return jsonify({"message": "Model deleted successfully", "model": model.name})
