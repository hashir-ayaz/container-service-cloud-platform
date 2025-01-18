from app import create_app, db
from app.models.user import User

app = create_app()


def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
