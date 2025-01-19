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
    user_id = db.Column(db.UUID, nullable=False)  # Remove FK, keep UUID reference
    image_name = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum(ContainerStatus),
        default=ContainerStatus.STOPPED,
        nullable=False,
    )
    config = db.Column(JSONB, nullable=True)  # JSONB for configuration
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<Container {self.id} - {self.image_name}>"
