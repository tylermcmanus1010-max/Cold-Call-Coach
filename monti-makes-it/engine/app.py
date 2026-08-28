"""Entry point.  Run with:  flask --app app run  (or gunicorn app:app)"""
from monti import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
