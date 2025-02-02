from app import db
import uuid
from sqlalchemy.dialects.postgresql import JSONB
from app.models.container import Container  # Keep Container relationship


class APIKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )  # UUID as primary key
    user_id = db.Column(
        db.Integer, nullable=False
    )  # No ForeignKey (user in auth service)
    container_id = db.Column(
        db.String(255), db.ForeignKey("containers.id"), nullable=False
    )  # FK to containers table
    key = db.Column(db.String(255), unique=True, nullable=False)  # Unique API key
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Remove User relationship (handled via API)
    container = db.relationship(
        "Container", backref=db.backref("api_keys", lazy=True)
    )  # Relationship to Container model

    def __repr__(self):
        return f"<APIKey {self.id} - Active: {self.is_active}>"
