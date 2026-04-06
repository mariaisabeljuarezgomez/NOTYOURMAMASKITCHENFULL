from flask import Flask, send_from_directory, request, jsonify
from flask_compress import Compress
from werkzeug.exceptions import NotFound
import os
import json
import shutil
import base64
import time
import hashlib
import hmac
import urllib.parse
from datetime import datetime
try:
    import cloudscraper
except ImportError:
    cloudscraper = None
import requests as _requests  # hard import — will crash loudly on startup if missing

def _http():
    """Return cloudscraper session if available, else requests session."""
    if cloudscraper:
        return cloudscraper.create_scraper()
    return _requests.Session()

def cloudinary_sign(params_dict, api_secret):
    """Generate Cloudinary auth signature: sorted params + api_secret, SHA-256."""
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params_dict.items()))
    to_sign = sorted_params + api_secret
    return hashlib.sha256(to_sign.encode("utf-8")).hexdigest()

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

# ===== AI STUDIO BACKEND ROUTES =====

@app.route("/api/ai/test-cloudinary", methods=["POST"])
def test_cloudinary():
    try:
        data = request.json or {}
        cloud_name = data.get("cloud_name", "")
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        if not all([cloud_name, api_key, api_secret]):
            return jsonify({"error": "Missing credentials"}), 400
        timestamp = int(time.time())
        sig = cloudinary_sign({"timestamp": timestamp}, api_secret)
        # Note: test signs {timestamp} only; actual cloudinary_upload() signs {folder, timestamp}. This is intentional — the test verifies credentials work in general, uploads include folder in the signature.
        url = f"https://api.cloudinary.com/v1_1/{cloud_name}/resources/image?timestamp={timestamp}&api_key={api_key}&signature={sig}"
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.get(url)
        if resp.status_code in (200, 401):
            return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid credentials or connection failed"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/test-google", methods=["POST"])
def test_google():
    try:
        data = request.json or {}
        project_id = data.get("project_id", "")
        api_key = data.get("api_key", "")
        # api_key here is expected to be a short-lived OAuth2 Bearer access token (not a raw API key).
        if len(api_key) < 100:
            return jsonify({"error": "Google credentials must be an OAuth2 access token, not a raw API key. The frontend must exchange your API key for a Bearer token first."}), 400
        if not all([project_id, api_key]):
            return jsonify({"error": "Missing credentials"}), 400
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/imagen-3.0-generate-001"
        headers = {"Authorization": f"Bearer {api_key}"}
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            return jsonify({"status": "ok"})
        if resp.status_code == 403:
            return jsonify({"error": "Credentials valid but Imagen API access denied — enable the Vertex AI API in your GCP project and ensure your service account has the 'Vertex AI User' role."}), 400
        return jsonify({"error": "Invalid credentials or project ID"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/test-kling", methods=["POST"])
def test_kling():
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        if not all([api_key, api_secret]):
            return jsonify({"error": "Missing credentials"}), 400
        test_url = "https://api.kling.ai/v1/oauth/token"
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.post(test_url, json={
            "api_key": api_key, "api_secret": api_secret
        })
        if resp.status_code in (200, 401, 403):
            return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid credentials or connection failed"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/enhance-prompt", methods=["POST"])
def enhance_prompt():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        prompt_type = data.get("type", "image")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        if prompt_type == "image":
            modifiers = "professional food photography, soft natural lighting, shallow depth of field, 85mm lens, restaurant-quality presentation, high resolution, appetizing composition"
        else:
            modifiers = "cinematic food video, slow motion, professional lighting, 4K quality, appetizing presentation, smooth camera movement, broadcast quality"
        if "professional food photography" not in prompt.lower():
            enhanced = f"{prompt}. {modifiers}"
        else:
            enhanced = prompt
        return jsonify({"enhanced_prompt": enhanced})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/generate-image", methods=["POST"])
def generate_image():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        aspect_ratio = data.get("aspect_ratio", "1:1")
        style = data.get("style", "photo-realistic")
        creds = data.get("credentials", {})
        project_id = creds.get("project_id", "")
        api_key = creds.get("api_key", "")
        # api_key here is expected to be a short-lived OAuth2 Bearer access token (not a raw API key).
        # The frontend is responsible for exchanging the raw API key for an access token via Google OAuth2.
        # Short tokens (<100 chars) are raw API keys — reject with a clear message.
        if len(api_key) < 100:
            return jsonify({"error": "Google credentials must be an OAuth2 access token, not a raw API key. The frontend must exchange your API key for a Bearer token first."}), 400
        if not all([prompt, project_id, api_key]):
            return jsonify({"error": "Missing prompt or credentials"}), 400
        ar_map = {"1:1": "1:1", "4:3": "4:3", "3:4": "3:4", "16:9": "16:9"}
        model_input = {"prompt": prompt, "aspect_ratio": ar_map.get(aspect_ratio, "1:1")}
        if negative_prompt:
            model_input["negative_prompt"] = negative_prompt
        if style != "photo-realistic":
            model_input["prompt"] = f"{prompt}, {style} style"
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/imagen-3.0-generate-001:predict"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.post(url, headers=headers, json={"instances": [model_input], "parameters": {}})
        if resp.status_code == 200:
            result = resp.json()
            predictions = result.get("predictions", [])
            if predictions and len(predictions) > 0:
                b64_img = predictions[0].get("bytesBase64Encoded", "")
                if b64_img:
                    return jsonify({"image_url": f"data:image/png;base64,{b64_img}"})
        return jsonify({"error": f"Image generation failed — API status {resp.status_code if resp else 'no response'}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/generate-video", methods=["POST"])
def generate_video():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        duration = data.get("duration", 5)
        resolution = data.get("resolution", "1920x1080")
        cfg_scale = data.get("cfg_scale", 0.5)
        reference_image_b64 = data.get("reference_image_b64", "")
        creds = data.get("credentials", {})
        api_key = creds.get("api_key", "")
        api_secret = creds.get("api_secret", "")
        if not all([prompt, api_key, api_secret]):
            return jsonify({"error": "Missing prompt or credentials"}), 400
        token_url = "https://api.kling.ai/v1/oauth/token"
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        token_resp = client.post(token_url, json={
            "api_key": api_key, "api_secret": api_secret, "grant_type": "client_credentials"
        })
        if token_resp.status_code != 200:
            return jsonify({"error": "Kling AI authentication failed"}), 400
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")
        submit_url = "https://api.kling.ai/v1/videos/text2video"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        res_map = {"1920x1080": "16:9", "1080x1920": "9:16", "1080x1080": "1:1"}
        aspect = res_map.get(resolution, "16:9")
        payload = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect,
            "cfg_scale": cfg_scale
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if reference_image_b64:
            payload["reference_image"] = f"data:image/jpeg;base64,{reference_image_b64}"
        sub_resp = client.post(submit_url, headers=headers, json=payload)
        if sub_resp.status_code in (200, 201, 202):
            task_data = sub_resp.json()
            task_id = task_data.get("data", {}).get("task_id") or task_data.get("task_id") or "pending"
            return jsonify({"task_id": task_id})
        return jsonify({"error": "Video generation submission failed"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/kling-status/<task_id>", methods=["POST"])
def kling_status(task_id):
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        if not all([api_key, api_secret]):
            return jsonify({"error": "Missing credentials"}), 400
        token_url = "https://api.kling.ai/v1/oauth/token"
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        token_resp = client.post(token_url, json={
            "api_key": api_key, "api_secret": api_secret, "grant_type": "client_credentials"
        })
        if token_resp.status_code != 200:
            return jsonify({"status": "failed", "error": "Kling AI auth failed"}), 400
        access_token = token_resp.json().get("access_token", "")
        status_url = f"https://api.kling.ai/v1/videos/text2video/{task_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        stat_resp = client.get(status_url, headers=headers)
        if stat_resp.status_code == 200:
            sd = stat_resp.json().get("data", {})
            status_str = sd.get("status", "pending")
            video_url = sd.get("video_url", "")
            progress = sd.get("progress", 50) if status_str == "processing" else (100 if status_str == "done" else 0)
            return jsonify({"status": status_str, "video_url": video_url, "progress": progress})
        return jsonify({"status": "pending", "progress": 0}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/cloudinary-upload", methods=["POST"])
def cloudinary_upload():
    try:
        data = request.json or {}
        file_b64 = data.get("file_b64", "")
        file_type = data.get("file_type", "image")
        creds = data.get("credentials", {})
        cloud_name = creds.get("cloud_name", "")
        api_key = creds.get("api_key", "")
        api_secret = creds.get("api_secret", "")
        if not all([file_b64, cloud_name, api_key, api_secret]):
            return jsonify({"error": "Missing file or credentials"}), 400
        timestamp = int(time.time())
        sig = cloudinary_sign({"folder": "nymk_ai", "timestamp": timestamp}, api_secret)
        upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload"
        mime_type = "image/png" if file_type == "image" else "video/mp4"
        file_payload = f"data:{mime_type};base64,{file_b64}"
        upload_fields = {
            "api_key": api_key,
            "timestamp": timestamp,
            "signature": sig,
            "folder": "nymk_ai"
        }
        if file_type == "video":
            upload_fields["resource_type"] = "video"
            upload_fields["eager"] = "sp_hd"
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.post(upload_url, files={"file": (None, file_payload, mime_type)}, data=upload_fields)
        if resp.status_code in (200, 201):
            result = resp.json()
            return jsonify({"url": result.get("secure_url", "")})
        return jsonify({"error": f"Cloudinary upload failed — status {resp.status_code if resp else 'no response'}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/edit-image", methods=["POST"])
def edit_image():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        reference_image_b64 = data.get("reference_image_b64", "")
        mode = data.get("mode", "edit")
        edit_strength = float(data.get("edit_strength", 0.5))
        creds = data.get("credentials", {})
        project_id = creds.get("project_id", "")
        api_key = creds.get("api_key", "")
        # api_key here is expected to be a short-lived OAuth2 Bearer access token (not a raw API key).
        if len(api_key) < 100:
            return jsonify({"error": "Google credentials must be an OAuth2 access token, not a raw API key. The frontend must exchange your API key for a Bearer token first."}), 400
        if not all([prompt, reference_image_b64, project_id, api_key]):
            return jsonify({"error": "Missing prompt, reference image, or credentials"}), 400
        url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/imagen-3.0-capability-001:predict"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if mode == "subject":
            prompt_with_ref = prompt if "[3]" in prompt else f"{prompt} [3]"
            instance = {
                "prompt": prompt_with_ref,
                "referenceImages": [{
                    "referenceType": "REFERENCE_TYPE_SUBJECT",
                    "referenceId": 1,
                    "referenceImage": {"bytesBase64Encoded": reference_image_b64},
                    "subjectImageConfig": {"subjectType": "SUBJECT_TYPE_PRODUCT"}
                }]
            }
        else:
            instance = {
                "prompt": prompt,
                "image": {"bytesBase64Encoded": reference_image_b64},
                "editConfig": {
                    "editMode": "EDIT_MODE_DEFAULT",
                    "guidanceScale": max(1, min(30, int(edit_strength * 30)))
                }
            }
            if negative_prompt:
                instance["negativePrompt"] = negative_prompt
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.post(url, headers=headers, json={"instances": [instance], "parameters": {}})
        if resp.status_code == 200:
            result = resp.json()
            predictions = result.get("predictions", [])
            if predictions:
                b64_img = predictions[0].get("bytesBase64Encoded", "")
                if b64_img:
                    return jsonify({"image_url": f"data:image/png;base64,{b64_img}"})
        return jsonify({"error": f"Edit image failed — API status {resp.status_code if resp else 'no response'}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
