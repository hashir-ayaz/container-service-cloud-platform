from app import db
import uuid
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum


class ContainerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    PENDING = "pending"


class Container(db.Model):
    __tablename__ = "containers"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )  # UUID as primary key
    user_id = db.Column(db.Integer, nullable=False)
    available_model_id = db.Column(
        db.Integer, db.ForeignKey("available_models.id"), nullable=False
    )  # Foreign key referencing `available_models.id`
    status = db.Column(
        db.Enum(ContainerStatus),
        default=ContainerStatus.STOPPED,
        nullable=False,
    )  # Enum for container status
    config = db.Column(JSONB, nullable=True)  # JSONB for configuration
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationship to AvailableModel
    available_model = db.relationship(
        "AvailableModel", backref=db.backref("containers", lazy=True)
    )

    def __repr__(self):
        return f"<Container {self.id} - Model {self.available_model_id} - Status {self.status}>"
