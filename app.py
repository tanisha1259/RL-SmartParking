from pathlib import Path
import importlib.util
import sys


BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

spec = importlib.util.spec_from_file_location("parkwise_backend_app", BACKEND_DIR / "app.py")
backend_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_app)
create_app = backend_app.create_app


application = create_app()


if __name__ == "__main__":
    from extensions import socketio  # noqa: E402

    if socketio:
        socketio.run(application, host="0.0.0.0", port=5001, debug=True)
    else:
        application.run(host="0.0.0.0", port=5001, debug=True)
