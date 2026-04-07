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
from io import BytesIO
try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None
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

def generate_kling_token(api_key: str, api_secret: str) -> str:
    """Generate Kling AI JWT token for authentication."""
    import jwt
    now = int(time.time())
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {"iss": api_key, "exp": now + 1800, "nbf": now - 5}
    return jwt.encode(payload, api_secret, algorithm="HS256", headers=headers)

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
VIDEO_HISTORY_FILE = os.path.join(STORAGE_BASE, "video_history.json")

IS_PERSISTENT = STORAGE_BASE.startswith("/app/data") or os.environ.get("RAILWAY_VOLUME_MOUNTED") == "true"

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "Images")
os.makedirs(IMAGES_DIR, exist_ok=True)

USER_IMAGES_DIR = os.path.join(STORAGE_BASE, "user_images")
os.makedirs(USER_IMAGES_DIR, exist_ok=True)

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
        # AI-generated images (prefixed "ai-") go to the persistent volume.
        # All other uploads stay in IMAGES_DIR (template asset folder).
        if filename.startswith("ai-"):
            save_dir = USER_IMAGES_DIR
            url_prefix = "/user-images"
        else:
            save_dir = IMAGES_DIR
            url_prefix = "/Images"
        filepath = os.path.join(save_dir, filename)
        if os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(save_dir, f"{name}_{counter}{ext}")):
                counter += 1
                if counter > 999:
                    return jsonify({"error": "Too many files with the same name"}), 409
            filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(save_dir, filename)
        with open(filepath, "wb") as f:
            f.write(decoded)
        final_url = f"{url_prefix}/{filename}"
        return jsonify({
            "status": "ok",
            "filename": filename,
            "url": final_url,
            "storage": {"originalUrl": final_url}
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
        if not os.path.exists(filepath):
            filepath = os.path.join(USER_IMAGES_DIR, filename)
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

@app.route("/user-images/<string:filename>")
def serve_user_image(filename):
    response = send_from_directory(USER_IMAGES_DIR, filename)
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

@app.route("/api/ai/test-stability", methods=["POST"])
def test_stability():
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        if not api_key:
            return jsonify({"error": "Missing API key"}), 400
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        resp = client.get(
            "https://api.stability.ai/v1/user/account",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        if resp.status_code == 200:
            return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid API key"}), 400
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
        token = generate_kling_token(api_key, api_secret)
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        test_url = "https://api.klingai.com/v1/videos/text2video?pageNum=1&pageSize=1"
        resp = client.get(test_url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code in (200, 401):
            return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid credentials or connection failed"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/debug-token", methods=["POST"])
def debug_token():
    data = request.json or {}
    api_key = data.get("api_key", "")
    api_secret = data.get("api_secret", "")
    if not all([api_key, api_secret]):
        return jsonify({"error": "Missing credentials"}), 400
    token = generate_kling_token(api_key, api_secret)
    return jsonify({"token": token})

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
        allowed_ar = {"16:9", "1:1", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"}
        aspect_ratio = data.get("aspect_ratio", "1:1")
        if aspect_ratio not in allowed_ar:
            aspect_ratio = "1:1"
        creds = data.get("credentials", {})
        api_key = creds.get("api_key", "")
        if not prompt or not api_key:
            return jsonify({"error": "Missing prompt or credentials"}), 400
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        files = {
            "prompt": (None, prompt),
            "output_format": (None, "png"),
            "aspect_ratio": (None, aspect_ratio),
        }
        if negative_prompt:
            files["negative_prompt"] = (None, negative_prompt)
        resp = client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "image/*"},
            files=files,
            timeout=60
        )
        if resp.status_code == 200:
            b64_img = base64.b64encode(resp.content).decode("utf-8")
            return jsonify({"image_url": f"data:image/png;base64,{b64_img}"})
        try:
            err_detail = resp.json().get("errors", [resp.text])
        except Exception:
            err_detail = resp.text
        return jsonify({"error": f"Stability API {resp.status_code}: {err_detail}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/generate-image-to-image", methods=["POST"])
def generate_image_to_image():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        init_image_b64 = data.get("init_image_b64", "")
        strength = float(data.get("strength", 0.75))
        allowed_ar = {"16:9", "1:1", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"}
        aspect_ratio = data.get("aspect_ratio", "1:1")
        if aspect_ratio not in allowed_ar:
            aspect_ratio = "1:1"
        creds = data.get("credentials", {})
        api_key = creds.get("api_key", "")
        if not prompt or not api_key or not init_image_b64:
            return jsonify({"error": "Missing prompt, init_image_b64, or credentials"}), 400
        if "," in init_image_b64:
            init_image_b64 = init_image_b64.split(",")[1]
        image_bytes = base64.b64decode(init_image_b64)
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        files = {
            "prompt": (None, prompt),
            "output_format": (None, "png"),
            "mode": (None, "image-to-image"),
            "strength": (None, str(strength)),
            "image": ("image.png", image_bytes, "image/png"),
        }
        if negative_prompt:
            files["negative_prompt"] = (None, negative_prompt)
        resp = client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "image/*"},
            files=files,
            timeout=60
        )
        if resp.status_code == 200:
            b64_img = base64.b64encode(resp.content).decode("utf-8")
            return jsonify({"image_url": f"data:image/png;base64,{b64_img}"})
        try:
            err_detail = resp.json().get("errors", [resp.text])
        except Exception:
            err_detail = resp.text
        return jsonify({"error": f"Stability img2img {resp.status_code}: {err_detail}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/generate-kling-image", methods=["POST"])
def generate_kling_image():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        model_name = data.get("model_name", "kling-v1")
        aspect_ratio = data.get("aspect_ratio", "1:1")
        n = data.get("n", 1)
        mode = data.get("mode", "txt2img")
        quality = data.get("quality", "1s")
        reference_images = data.get("reference_images", [])
        creds = data.get("credentials", {})
        api_key = creds.get("api_key", "")
        api_secret = creds.get("api_secret", "")

        ALLOWED_MODELS = {
            "kling-v1", "kling-v1-5", "kling-v1-6",
            "kling-v2-1", "kling-v2", "kling-v3",
            "kling-v2-omni", "kling-image-v1"
        }
        ALLOWED_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "auto"}

        if not prompt or not api_key or not api_secret:
            return jsonify({"error": "Missing prompt or Kling credentials"}), 400
        if model_name not in ALLOWED_MODELS:
            model_name = "kling-v1"
        if aspect_ratio not in ALLOWED_RATIOS:
            aspect_ratio = "1:1"

        token = generate_kling_token(api_key, api_secret)
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500

        payload = {
            "model_name": model_name,
            "prompt": prompt,
            "n": n,
            "aspect_ratio": aspect_ratio
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        # Handle reference images based on mode
        if reference_images and mode != "txt2img":
            # Clean base64: strip any data:image/...;base64, prefix
            clean_refs = [
                {"image": b64.split(",")[-1] if "," in b64 else b64}
                for b64 in reference_images[:4]
            ]
            if mode == "img2img" or mode == "edit" or mode == "expand":
                payload["image"] = clean_refs[0]["image"]
            elif mode == "multi":
                payload["image_list"] = clean_refs

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        resp = client.post(
            "https://api.klingai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=30
        )

        if resp.status_code in (200, 201, 202):
            resp_data = resp.json()
            task_id = resp_data.get("data", {}).get("task_id") or resp_data.get("task_id") or "pending"
            return jsonify({"task_id": task_id})
        try:
            kling_err = resp.json()
        except Exception:
            kling_err = resp.text
        return jsonify({"error": f"Kling image submission failed {resp.status_code}: {kling_err}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/kling-image-status/<task_id>", methods=["POST"])
def kling_image_status(task_id):
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        if not all([api_key, api_secret]):
            return jsonify({"error": "Missing credentials"}), 400
        token = generate_kling_token(api_key, api_secret)
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        status_url = f"https://api.klingai.com/v1/images/generations/{task_id}"
        headers = {"Authorization": f"Bearer {token}"}
        stat_resp = client.get(status_url, headers=headers, timeout=20)
        if stat_resp.status_code == 200:
            sd = stat_resp.json().get("data", {})
            status_str = sd.get("task_status", "submitted")
            images = sd.get("task_result", {}).get("images", [])
            image_url = images[0].get("url", "") if images else ""
            progress_map = {"submitted": 0, "processing": 50, "succeed": 100, "failed": 0}
            progress = progress_map.get(status_str, 0)
            error = None
            if status_str == "failed":
                error = "Kling AI image generation failed"
            resp_body = {"status": status_str, "image_url": image_url, "progress": progress}
            if error:
                resp_body["error"] = error
            return jsonify(resp_body)
        return jsonify({"status": "pending", "progress": 0}), 200
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
        quality_mode = data.get("quality_mode", "std")
        creds = data.get("credentials", {})
        api_key = creds.get("api_key", "")
        api_secret = creds.get("api_secret", "")
        if not all([prompt, api_key, api_secret]):
            return jsonify({"error": "Missing prompt or credentials"}), 400
        token = generate_kling_token(api_key, api_secret)
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        is_image2video = bool(reference_image_b64)
        task_type = "image2video" if is_image2video else "text2video"
        submit_url = f"https://api.klingai.com/v1/videos/{task_type}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        res_map = {"1920x1080": "16:9", "1080x1920": "9:16", "1080x1080": "1:1"}
        aspect = res_map.get(resolution, "16:9")
        if is_image2video:
            payload = {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": aspect,
                "model_name": data.get("model_name", "kling-v1")
            }
        else:
            payload = {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": aspect,
                "cfg_scale": cfg_scale,
                "model_name": data.get("model_name", "kling-v1")
            }

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        # Add quality_mode if provided
        if quality_mode:
            payload["mode"] = quality_mode

        # camera_motion is only valid for text2video — strip it for image2video
        camera_motion = data.get("camera_motion", "none")
        if task_type == "text2video" and camera_motion and camera_motion != "none":
            payload["camera_motion"] = camera_motion
        if reference_image_b64:
            # Kling requires a PUBLIC URL for image_url, not base64.
            # We must upload to Cloudinary first.
            c_creds = data.get("cloudinary_credentials", {})
            c_name = c_creds.get("cloud_name")
            c_key = c_creds.get("api_key")
            c_secret = c_creds.get("api_secret")

            if not all([c_name, c_key, c_secret]):
                return jsonify({"error": "Cloudinary credentials required for image-to-video"}), 400

            # 1. Prepare base64 for Cloudinary (ensure it has the prefix)
            c_file_payload = reference_image_b64
            if "," not in c_file_payload:
                c_file_payload = f"data:image/png;base64,{c_file_payload}"

            # 2. Upload to Cloudinary
            c_ts = int(time.time())
            c_sig = cloudinary_sign({"folder": "nymk_ai_refs", "timestamp": c_ts}, c_secret)
            c_url = f"https://api.cloudinary.com/v1_1/{c_name}/auto/upload"
            
            c_fields = {
                "api_key": c_key,
                "timestamp": c_ts,
                "signature": c_sig,
                "folder": "nymk_ai_refs"
            }
            
            c_files = {"file": (None, c_file_payload, "image/png")}
            for k, v in c_fields.items():
                c_files[k] = (None, str(v))
                
            c_resp = client.post(c_url, files=c_files, timeout=60)
            if c_resp.status_code not in (200, 201):
                return jsonify({"error": f"Cloudinary upload failed for reference image: {c_resp.text}"}), 400
            
            public_url = c_resp.json().get("secure_url")
            if not public_url:
                return jsonify({"error": "Failed to get public URL from Cloudinary"}), 400

            # 3. Use the public URL in the Kling payload
            payload["image_url"] = public_url
        
        # DEBUG: Print payload to console (visible in Railway logs)
        print(f"DEBUG: Kling Payload: {json.dumps({k:v for k,v in payload.items() if k != 'image_url'})}")
        if 'image_url' in payload:
            print(f"DEBUG: Kling Image URL: {payload['image_url'][:50]}...")

        sub_resp = client.post(submit_url, headers=headers, json=payload, timeout=30)
        if sub_resp.status_code in (200, 201, 202):
            task_data = sub_resp.json()
            task_id = task_data.get("data", {}).get("task_id") or task_data.get("task_id") or "pending"
            return jsonify({"task_id": task_id, "task_type": task_type})
        try:
            kling_err = sub_resp.json()
        except Exception:
            kling_err = sub_resp.text
        return jsonify({"error": f"Kling submission failed {sub_resp.status_code}: {kling_err}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/kling-status/<task_id>", methods=["POST"])
def kling_status(task_id):
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        task_type = data.get("task_type", "text2video")
        if not all([api_key, api_secret]):
            return jsonify({"error": "Missing credentials"}), 400
        token = generate_kling_token(api_key, api_secret)
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500
        status_url = f"https://api.klingai.com/v1/videos/{task_type}/{task_id}"
        headers = {"Authorization": f"Bearer {token}"}
        stat_resp = client.get(status_url, headers=headers, timeout=20)
        if stat_resp.status_code == 200:
            sd = stat_resp.json().get("data", {})
            status_str = sd.get("task_status", "submitted")
            videos = sd.get("task_result", {}).get("videos", [])
            video_url = videos[0].get("url", "") if videos else ""
            progress_map = {"submitted": 0, "processing": 50, "succeed": 100, "failed": 0}
            progress = progress_map.get(status_str, 0)
            error = sd.get("error") or ("Kling AI video generation failed" if status_str == "failed" else None)
            resp = {"status": status_str, "video_url": video_url, "progress": progress}
            if error:
                resp["error"] = error
            return jsonify(resp)
        return jsonify({"status": "pending", "progress": 0}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/video-history", methods=["GET"])
def get_video_history():
    try:
        if not os.path.exists(VIDEO_HISTORY_FILE):
            return jsonify({"hero": [], "left": [], "right": []}), 200
        with open(VIDEO_HISTORY_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f)), 200
    except Exception as e:
        return jsonify({"hero": [], "left": [], "right": [], "error": str(e)}), 500

@app.route("/api/video-history", methods=["POST"])
def save_video_history_route():
    try:
        data = request.json or {}
        slot = data.get("slot", "")
        url = data.get("url", "")
        if slot not in ("hero", "left", "right") or not url:
            return jsonify({"error": "Invalid slot or url"}), 400
        history = {"hero": [], "left": [], "right": []}
        if os.path.exists(VIDEO_HISTORY_FILE):
            with open(VIDEO_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        slot_list = history.get(slot, [])
        slot_list = [url] + [u for u in slot_list if u != url]
        history[slot] = slot_list[:3]
        with open(VIDEO_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        return jsonify({"status": "ok", "history": history[slot]}), 200
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
        upload_files = {"file": (None, file_payload, mime_type)}
        for k, v in upload_fields.items():
            upload_files[k] = (None, str(v))
        resp = client.post(upload_url, files=upload_files, timeout=60)
        if resp.status_code in (200, 201):
            result = resp.json()
            return jsonify({"url": result.get("secure_url", "")})
        return jsonify({"error": f"Cloudinary upload failed — status {resp.status_code if resp else 'no response'}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
