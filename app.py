# Triggering redeployment to verify volume persistence (v1.1.2)
from flask import Flask, send_from_directory, abort, request, jsonify
from flask_compress import Compress
import os
import json
import shutil
from datetime import datetime

app = Flask(__name__)

# Optimize Compression for PageSpeed & Performance
app.config["COMPRESS_MIN_SIZE"] = 0  # Compress everything, even small JSONs
app.config["COMPRESS_MIMETYPES"] = [
    "text/html", "text/css", "text/xml", 
    "application/json", "application/javascript", "application/octet-stream",
    "font/ttf", "font/otf", "font/woff", "font/woff2", "font/x-font-ttf",
    "image/svg+xml"
]
Compress(app)

# --- STORAGE CONFIGURATION ---
STORAGE_BASE = os.environ.get("STORAGE_DIR", "/app/data")
if not os.path.exists(STORAGE_BASE):
    try:
        os.makedirs(STORAGE_BASE, exist_ok=True)
    except Exception:
        STORAGE_BASE = "./data"
        os.makedirs(STORAGE_BASE, exist_ok=True)

DATA_FILE = os.path.join(STORAGE_BASE, "menu_data.json")
BACKUP_DIR = os.path.join(STORAGE_BASE, "backups")

IS_PERSISTENT = STORAGE_BASE.startswith("/app/data") or os.environ.get("RAILWAY_VOLUME_MOUNTED") == "true"

def validate_schema(data):
    if "version" in data and "elements" in data:
        return isinstance(data["elements"], list)
    required_keys = ["zoom", "scroll", "elements"]
    if all(k in data for k in required_keys):
        return isinstance(data["elements"], list)
    return False

@app.route("/")
def index():
    if not os.path.exists("index.html"):
        return "Critical Error: index.html not found. Please run build_app.py first.", 500
    return send_from_directory(".", "index.html")

@app.route("/api/menu", methods=["GET"])
def get_menu():
    status_info = {"is_persistent": IS_PERSISTENT, "storage_base": STORAGE_BASE}
    if not os.path.exists(DATA_FILE):
        return jsonify({"elements": [], "zoom": 1, "scroll": {"x": 0, "y": 0}, "info": "initial", "status": status_info}), 200
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["status"] = status_info
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "status": status_info}), 500

@app.route("/api/menu", methods=["POST"])
def save_menu():
    data = request.json
    if not data or not validate_schema(data):
        return jsonify({"error": "Invalid schema"}), 400
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        if os.path.exists(DATA_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"menu_data_{timestamp}.json")
            shutil.copy2(DATA_FILE, backup_path)
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_file, DATA_FILE)
        return jsonify({"status": "success", "backup": f"menu_data_{timestamp}.json" if 'timestamp' in locals() else None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/menu/reset", methods=["POST"])
def reset_menu():
    """Wipe the saved menu_data.json so stale/poisoned data never loads again."""
    try:
        if os.path.exists(DATA_FILE):
            # Back it up first before wiping
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"menu_data_RESET_{timestamp}.json")
            shutil.copy2(DATA_FILE, backup_path)
            os.remove(DATA_FILE)
        return jsonify({"status": "reset_ok", "message": "Saved data cleared. Page will now always load from embedded index.html state."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(".", path)

# --- IMAGE PERSISTENCE (Phase 13) ---
import base64
from pathlib import Path

IMAGES_DIR = os.path.join(STORAGE_BASE, "user_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    try:
        data = request.json
        filename = data.get("filename", f"upload_{int(datetime.now().timestamp())}.png")
        img_data = data.get("data", "")
        if "," in img_data:
            img_data = img_data.split(",")[1]
        filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(img_data))
        return jsonify({"status": "ok", "filename": filename, "url": f"/user-images/{filename}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete-image/<filename>", methods=["DELETE"])
def delete_image(filename):
    try:
        filepath = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"status": "deleted"}), 200
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/list-images", methods=["GET"])
def list_images():
    try:
        files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        return jsonify({"images": [{"filename": f, "url": f"/user-images/{f}"} for f in sorted(files)]}), 200
    except Exception as e:
        return jsonify({"images": []}), 200

@app.route("/user-images/<path:filename>")
def serve_user_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
