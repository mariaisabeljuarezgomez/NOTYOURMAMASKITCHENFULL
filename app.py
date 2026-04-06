from flask import Flask, send_from_directory, request, jsonify
from flask_compress import Compress
from werkzeug.exceptions import NotFound
import os
import json
import shutil
import base64
from datetime import datetime

app = Flask(__name__)

# Optimize Compression for PageSpeed & Performance
app.config["COMPRESS_MIN_SIZE"] = 500  # Only compress responses larger than 500 bytes
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

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "Images")
os.makedirs(IMAGES_DIR, exist_ok=True)

PROTECTED_ASSETS = {
    "Asset1.png", "Asset2.png", "Asset3.png", "Asset4.png",
    "Asset6.png", "Asset7.png", "Asset8.png", "Asset9.png",
    "Asset10.png", "Asset11.png", "Asset12.png", "Asset13.png", "Asset14.png"
}

MAGIC_BYTES = [
    b"\x89PNG",
    b"\xff\xd8",
    b"RIFF",
]

def prune_backups(backup_dir, keep=20):
    try:
        files = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith(".json")],
            reverse=True
        )
        for old in files[keep:]:
            os.remove(os.path.join(backup_dir, old))
    except Exception as e:
        print(f"[prune_backups] Failed to prune backups in {backup_dir}: {e}")

def validate_schema(data):
    if not isinstance(data, dict):
        return False
    if data.get("version") != 2:
        return False
    return isinstance(data.get("elements"), list)

@app.route("/")
def index():
    if not os.path.exists("index.html"):
        return "Critical Error: index.html not found. Please run build_app.py first.", 500
    response = send_from_directory(".", "index.html")
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

@app.route("/api/menu", methods=["GET"])
def get_menu():
    status_info = {"is_persistent": IS_PERSISTENT, "storage_base": STORAGE_BASE}
    if not os.path.exists(DATA_FILE):
        return jsonify({"elements": [], "zoom": 1, "scroll": {"x": 0, "y": 0}, "info": "initial", "status": status_info}), 200
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return jsonify({**data, "status": status_info})
    except Exception as e:
        return jsonify({"error": str(e), "status": status_info}), 500

@app.route("/api/menu", methods=["POST"])
def save_menu():
    if request.content_length and request.content_length > 5_000_000:
        return jsonify({"error": "Payload too large"}), 413
    data = request.json
    if data is None:
        return jsonify({"error": "Request body is required"}), 400
    if not validate_schema(data):
        return jsonify({"error": "Invalid schema"}), 400
    try:
        timestamp = None
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
        prune_backups(BACKUP_DIR)
        return jsonify({"status": "success", "backup": f"menu_data_{timestamp}.json" if timestamp else None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/menu/reset", methods=["POST"])
def reset_menu():
    """Wipe the saved menu_data.json so stale/poisoned data never loads again."""
    try:
        if os.path.exists(DATA_FILE):
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"menu_data_RESET_{timestamp}.json")
            shutil.copy2(DATA_FILE, backup_path)
            os.remove(DATA_FILE)
        prune_backups(BACKUP_DIR)
        return jsonify({"status": "reset_ok", "message": "Saved data cleared. Page will now always load from embedded index.html state."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/menu/backups", methods=["GET"])
def list_backups():
    """List all backup files — most recent first."""
    try:
        if not os.path.exists(BACKUP_DIR):
            return jsonify({"backups": []}), 200
        files = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")],
            reverse=True
        )
        return jsonify({"backups": files}), 200
    except Exception as e:
        return jsonify({"backups": [], "error": str(e)}), 500

@app.route("/api/menu/restore/<filename>", methods=["POST"])
def restore_backup(filename):
    """Restore a specific backup file to menu_data.json."""
    try:
        # Safety: only allow filenames that look like our backups (no path traversal)
        if "/" in filename or "\\" in filename or not filename.endswith(".json"):
            return jsonify({"error": "Invalid filename"}), 400
        src = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(src):
            return jsonify({"error": "Backup file not found: " + filename}), 404
        with open(src, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        if not validate_schema(backup_data):
            return jsonify({"error": "Backup is not a valid V2 document — restore aborted"}), 400
        # Backup current state before overwriting (just in case)
        if os.path.exists(DATA_FILE):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(DATA_FILE, os.path.join(BACKUP_DIR, f"menu_data_pre_restore_{ts}.json"))
        shutil.copy2(src, DATA_FILE)
        prune_backups(BACKUP_DIR)
        return jsonify({"status": "restored", "from": filename}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/menu-debug", methods=["GET"])
def debug_menu():
    """Temporary debug endpoint — returns raw disk JSON + metadata for diagnosis."""
    debug_key = os.environ.get("DEBUG_KEY", "")
    if not debug_key or request.args.get("key") != debug_key:
        return jsonify({"error": "Unauthorized"}), 403
    debug_info = {
        "data_file_path": DATA_FILE,
        "storage_base": STORAGE_BASE,
        "is_persistent": IS_PERSISTENT,
        "file_exists": os.path.exists(DATA_FILE),
    }
    if not os.path.exists(DATA_FILE):
        return jsonify({"debug": debug_info, "data": None, "error": "No saved file on disk"}), 200
    try:
        file_size = os.path.getsize(DATA_FILE)
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        debug_info["file_size_bytes"] = file_size
        debug_info["element_count"] = len(raw.get("elements", []))
        debug_info["element_types"] = {}
        for el in raw.get("elements", []):
            t = el.get("type", "unknown")
            debug_info["element_types"][t] = debug_info["element_types"].get(t, 0) + 1
        return jsonify({"debug": debug_info, "data": raw}), 200
    except Exception as e:
        return jsonify({"debug": debug_info, "error": str(e)}), 500

@app.route("/api/render-check", methods=["GET"])
def render_check():
    """Visual regression check endpoint: verifies all image assets exist on disk."""
    if not os.path.exists(DATA_FILE):
        return jsonify({"error": "No saved data to check"}), 404

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Build src lookup from saved doc assets
        assets_list = data.get("assets", [])
        asset_src_map = {}
        for a in assets_list:
            aid = a.get("id") or a.get("assetId")
            src = (a.get("storage") or {}).get("originalUrl") or a.get("src", "")
            if aid and src:
                asset_src_map[aid] = src

        results = []
        for el in data.get("elements", []):
            if el.get("type") == "image":
                asset_id = el.get("assetId")
                base_src = el.get("src")

                # Resolve exactly like viewer.html
                resolved_src = asset_src_map.get(asset_id, "") if asset_id else ""
                if not resolved_src:
                    resolved_src = base_src or ""

                exists = False
                if resolved_src:
                    # Strip leading slash to map to local filesystem correctly
                    local_path = resolved_src.lstrip("/")
                    full_path = os.path.join(os.path.dirname(__file__), local_path)
                    exists = os.path.exists(full_path)

                results.append({
                    "element_id": el.get("id"),
                    "assetId": asset_id,
                    "original_src": base_src,
                    "resolved_src": resolved_src,
                    "exists_on_disk": exists
                })

        return jsonify({
            "total_images": len(results),
            "missing_images": sum(1 for r in results if not r["exists_on_disk"]),
            "details": results
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/<path:path>")
def static_proxy(path):
    try:
        response = send_from_directory(".", path)
        if path.lower().endswith((".ttf", ".js")):
            response.headers["Cache-Control"] = "max-age=604800, public"
        return response
    except NotFound:
        return jsonify({"error": "Not found", "path": path}), 404


@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        filename = os.path.basename(data.get("filename", f"upload_{int(datetime.now().timestamp())}.png"))
        allowed_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            return jsonify({"error": "Invalid file type"}), 400
        # Support both 'image' and 'data' keys for maximum compatibility
        img_data = data.get("data") or data.get("image", "")
        if not img_data:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_data:
            img_data = img_data.split(",")[1]
        try:
            decoded = base64.b64decode(img_data)
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400
        if not any(decoded[:len(sig)] == sig for sig in MAGIC_BYTES):
            return jsonify({"error": "File content does not match a supported image type"}), 400
        filepath = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(IMAGES_DIR, f"{name}_{counter}{ext}")):
                counter += 1
                if counter > 999:
                    return jsonify({"error": "Too many files with the same name"}), 409
            filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(decoded)
        return jsonify({
            "status": "ok",
            "filename": filename,
            "url": f"/Images/{filename}",
            "storage": {"originalUrl": f"/Images/{filename}"}
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete-asset/<filename>", methods=["DELETE"])
def delete_asset(filename):
    try:
        filename = os.path.basename(filename)
        if filename in PROTECTED_ASSETS:
            return jsonify({"error": "Cannot delete template asset"}), 403
            
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
        files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        return jsonify({
            "images": [{"filename": f, "url": f"/Images/{f}"} for f in sorted(files)]
        }), 200
    except Exception as e:
        return jsonify({"images": [], "error": str(e)}), 500

@app.route("/Images/<string:filename>")
def serve_root_image(filename):
    response = send_from_directory(IMAGES_DIR, filename)
    response.headers["Cache-Control"] = "max-age=604800, public"
    return response

@app.route('/menu')
def customer_viewer():
    response = send_from_directory('.', 'viewer.html')
    response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
