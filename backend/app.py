from flask import Flask
from flask_cors import CORS

from extensions import socketio
from routes.api import api_bp


def create_app():
    app = Flask(__name__)
    CORS(app)

    if socketio:
        socketio.init_app(app)

    app.register_blueprint(api_bp)

    return app


if __name__ == "__main__":
    app = create_app()

    if socketio:
        socketio.run(app, host="0.0.0.0", port=5001, debug=True)
    else:
        app.run(host="0.0.0.0", port=5001, debug=True)