import atexit
from pathlib import Path

from flask import Flask, send_from_directory
from flask import jsonify

from backend.database import Database
from backend.routes import create_blueprint
from backend.wechat_client import WeChatClient
from backend.wechat_client import WeChatClientError


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
app = Flask(__name__, static_folder=str(ROOT / "frontend"), static_url_path="")
database = Database(DATA_DIR / "wechat.db")
client = WeChatClient(DATA_DIR / "browser-profile")
app.register_blueprint(create_blueprint(database, client))


@app.errorhandler(WeChatClientError)
def handle_client_error(error):
    return jsonify({"ok": False, "error": {"code": error.code, "message": error.message}}), 400


@app.errorhandler(ValueError)
def handle_input_error(error):
    return jsonify({"ok": False, "error": {"code": "INPUT", "message": str(error)}}), 400


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/<path:path>")
def static_files(path):
    file_path = Path(app.static_folder) / path
    if file_path.is_file():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


@atexit.register
def close_client():
    client.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5200, debug=True)
