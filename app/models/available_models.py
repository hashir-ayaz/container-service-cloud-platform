from app import db


class AvailableModel(db.Model):
    __tablename__ = "available_models"

    id = db.Column(db.Integer, primary_key=True)  # Unique identifier for the model
    name = db.Column(db.String(100), nullable=False, unique=True)  # Name of the model
    description = db.Column(db.Text, nullable=True)  # Brief description of the model
    docker_image = db.Column(
        db.String(255), nullable=False, unique=True
    )  # Docker image path (e.g., "myrepo/myimage:tag")
    version = db.Column(
        db.String(50), nullable=False, default="latest"
    )  # Version of the Docker image
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now()
    )  # Timestamp for when the record was created
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )  # Timestamp for last update
    is_active = db.Column(
        db.Boolean, nullable=False, default=True
    )  # Whether the model is currently available for deployment

    def __repr__(self):
        return f"<AvailableModel(name={self.name}, docker_image={self.docker_image}, version={self.version})>"
