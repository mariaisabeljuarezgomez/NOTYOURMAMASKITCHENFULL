# Triggering redeployment to verify volume persistence (v1.1.1)
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
# Default to /app/data based on user's Railway volume mount point
# Fallback to local './data' for development
STORAGE_BASE = os.environ.get("STORAGE_DIR", "/app/data")
if not os.path.exists(STORAGE_BASE):
    try:
        os.makedirs(STORAGE_BASE, exist_ok=True)
    except Exception:
        # If /app/data is not writable (e.g. local dev), fallback to local
        STORAGE_BASE = "./data"
        os.makedirs(STORAGE_BASE, exist_ok=True)

DATA_FILE = os.path.join(STORAGE_BASE, "menu_data.json")
BACKUP_DIR = os.path.join(STORAGE_BASE, "backups")

# Track if we are likely on persistent storage
IS_PERSISTENT = STORAGE_BASE.startswith("/app/data") or os.environ.get("RAILWAY_VOLUME_MOUNTED") == "true"

def validate_schema(data):
    """Basic validation for menu data schema (supports both V1 and V2)."""
    # V2 check
    if "version" in data and "elements" in data:
        return isinstance(data["elements"], list)
    
    # V1 check
    required_keys = ["zoom", "scroll", "elements"]
    if all(k in data for k in required_keys):
        return isinstance(data["elements"], list)
        
    return False

@app.route("/")
def index():
    # Ensure index.html exists before serving
    if not os.path.exists("index.html"):
        return "Critical Error: index.html not found. Please run build_app.py first.", 500
    return send_from_directory(".", "index.html")

@app.route("/api/menu", methods=["GET"])
def get_menu():
    status_info = {
        "is_persistent": IS_PERSISTENT,
        "storage_base": STORAGE_BASE
    }
    
    if not os.path.exists(DATA_FILE):
        return jsonify({
            "elements": [], 
            "zoom": 1, 
            "scroll": {"x": 0, "y": 0}, 
            "info": "initial",
            "status": status_info
        }), 200
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
        # 1. Create backups directory if not exists
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        # 2. Versioned Backup before overwrite
        if os.path.exists(DATA_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"menu_data_{timestamp}.json")
            shutil.copy2(DATA_FILE, backup_path)

        # 3. Atomic Save (Write to temp, then rename)
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        # Replace original file with temp file (atomic on POSIX, reasonably safe on Windows)
        os.replace(temp_file, DATA_FILE)
        
        return jsonify({"status": "success", "backup": f"menu_data_{timestamp}.json" if 'timestamp' in locals() else None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/<path:path>")
def static_proxy(path):
    # Serve other static files if they exist
    return send_from_directory(".", path)

if __name__ == "__main__":
    # Railway provides the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
