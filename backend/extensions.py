try:
    from flask_socketio import SocketIO
except ImportError:
    SocketIO = None

socketio = SocketIO(cors_allowed_origins="*") if SocketIO else None