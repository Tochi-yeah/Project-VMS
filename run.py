import eventlet
eventlet.monkey_patch()

from app import create_app, socketio
import os

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 5000 for local default
    socketio.run(app, host="0.0.0.0", port=port)