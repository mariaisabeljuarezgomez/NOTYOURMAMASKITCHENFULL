from flask import Flask, send_from_directory, request, jsonify, Response
from flask_compress import Compress
from werkzeug.exceptions import NotFound
import os
import json
import shutil
import base64
import time
import uuid
import hashlib
import hmac
import urllib.parse
from datetime import datetime
from io import BytesIO
import psycopg2
from psycopg2.extras import RealDictCursor
try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None
try:
    import cloudscraper
except ImportError:
    cloudscraper = None
import requests as _requests

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

# --- SITE PASSWORD (change via Railway env var SITE_PASSWORD) ---
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "menueditorpro")

# Optimize Compression for PageSpeed & Performance
app.config["COMPRESS_MIN_SIZE"] = 500
app.config["COMPRESS_MIMETYPES"] = [
    "text/html", "text/css", "text/xml", 
    "application/json", "application/javascript", "application/octet-stream",
    "font/ttf", "font/otf", "font/woff", "font/woff2", "font/x-font-ttf",
    "image/svg+xml"
]
Compress(app)

# --- DATABASE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "Images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Default Menu Template
DEFAULT_MENU_DATA = {"version": 2, "elements": []}

def init_db():
    if not DATABASE_URL:
        return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        
        # Ensure schema matches reality (Option B implementation)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                canvas_json JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Restoration: Create video_history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS video_history (
                id SERIAL PRIMARY KEY,
                slot TEXT NOT NULL,         -- 'hero', 'left', or 'right'
                url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Access control: IP whitelist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ip_whitelist (
                ip TEXT PRIMARY KEY,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Access control: full access log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id SERIAL PRIMARY KEY,
                ip TEXT NOT NULL,
                page TEXT NOT NULL,
                event TEXT NOT NULL,
                user_agent TEXT,
                duration_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Site-wide settings (key-value store)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Seed default: viewer is locked (DO NOTHING if already exists)
        cur.execute("""
            INSERT INTO site_settings (key, value)
            VALUES ('viewer_public', 'false')
            ON CONFLICT (key) DO NOTHING
        """)

        # MIGRATION (one-time): Credentials used to live inside the menu document
        # (canvas_json.aiCredentials). They now live separately in site_settings
        # under 'ai_credentials'. On first boot after this change, copy any
        # existing credentials from the 'main' menu document into the new store
        # (only if the new store is empty), then strip them from the document so
        # they can never leak via the public /api/menu endpoint again.
        cur.execute("SELECT value FROM site_settings WHERE key = 'ai_credentials'")
        if not cur.fetchone():
            cur.execute("SELECT canvas_json FROM sessions WHERE id = 'main'")
            main_row = cur.fetchone()
            migrated = None
            if main_row and main_row[0]:
                try:
                    main_doc = main_row[0] if isinstance(main_row[0], dict) else json.loads(main_row[0])
                    old_creds = main_doc.get('aiCredentials') if isinstance(main_doc, dict) else None
                    if isinstance(old_creds, dict) and any(str(v).strip() for v in old_creds.values()):
                        migrated = {f: str(old_creds.get(f, '') or '').strip() for f in CRED_FIELDS}
                except Exception:
                    migrated = None
            if migrated:
                cur.execute(
                    """INSERT INTO site_settings (key, value, updated_at)
                       VALUES ('ai_credentials', %s, CURRENT_TIMESTAMP)
                       ON CONFLICT (key) DO NOTHING""",
                    (json.dumps(migrated),)
                )
                print("DB: Migrated aiCredentials from menu document to site_settings")

        # Migration: If id is integer, convert to TEXT
        cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'sessions' AND column_name = 'id'")
        row = cur.fetchone()
        if row and row[0] == 'integer':
            cur.execute("ALTER TABLE sessions ALTER COLUMN id TYPE TEXT")
            print("DB: Migrated id column to TEXT")

        # Ensure 'main' record exists
        cur.execute("SELECT id FROM sessions WHERE id = 'main'")
        if not cur.fetchone():
            # Try to swallow the latest existing record into 'main' or seed default
            cur.execute("SELECT canvas_json FROM sessions ORDER BY updated_at DESC LIMIT 1")
            prev = cur.fetchone()
            canvas_data = prev[0] if prev else DEFAULT_MENU_DATA
            cur.execute("INSERT INTO sessions (id, canvas_json) VALUES ('main', %s) ON CONFLICT (id) DO NOTHING", (json.dumps(canvas_data),))
            print("DB: Initialized 'main' session record")
            
        # Ensure 'backup' record exists for rolling auto-backup
        cur.execute("SELECT id FROM sessions WHERE id = 'backup'")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO sessions (id, canvas_json) VALUES ('backup', %s) ON CONFLICT (id) DO NOTHING",
                (json.dumps(DEFAULT_MENU_DATA),)
            )
            print("DB: Initialized 'backup' session record")

        conn.commit()
        cur.close()
    except Exception as e:
        print(f"init_db FATAL: {e}", flush=True)
        # Prevent app from starting with a broken or uninitialized database connection
        # This protects against silent data loss.
        import sys
        sys.exit(f"FATAL: Database initialization failed: {e}")
    finally:
        if conn:
            conn.close()

# Initialize DB on startup
init_db()

PROTECTED_ASSETS = {
    "Asset1.png", "Asset2.png", "Asset3.png", "Asset4.png",
    "Asset6.png", "Asset7.png", "Asset8.png", "Asset9.png",
    "Asset10.png", "Asset11.png", "Asset12.png", "Asset13.png", "Asset14.png"
}

MAGIC_BYTES = [b"\x89PNG", b"\xff\xd8", b"RIFF"]

def validate_schema(data):
    if not isinstance(data, dict): return False
    if not isinstance(data.get("elements"), list): return False
    if not all(isinstance(e, dict) and 'id' in e and 'type' in e for e in data.get('elements', [])): return False
    if "assets" in data and not isinstance(data["assets"], list): return False
    # Anti-wipe guard: reject a payload with no elements AND no assets. This
    # blocks the empty-wipe attack (POST {elements:[]}) while still accepting
    # any genuine menu document, which always has at least one element.
    if len(data.get('elements', [])) == 0 and len(data.get('assets', [])) == 0:
        return False
    return True

# ─── SERVER-SIDE AUTH GATE ────────────────────────────────────────────────────
# The frontend password overlay is cosmetic only. This gate enforces access
# control at the server so that:
#   • The lock page + unlock endpoint are reachable by anyone.
#   • Static assets (fonts, JS, images, manuals) are reachable by anyone.
#   • The public customer viewer (/menu + its /api/menu polling read) is reachable
#     only when the owner has set viewer_public=true via the admin dashboard.
#   • EVERYTHING else under /api/ (writes, credentials, admin, history, uploads)
#     requires the requesting IP to be whitelisted (i.e. entered the password).
#
# Safe paths that NEVER require auth:
PUBLIC_PATHS = {
    '/api/auth/check', '/api/auth/unlock', '/api/auth/log', '/api/auth/page-view'
}

# Paths that require auth even when viewer_public is on:
PROTECTED_API_PATHS = {
    '/api/credentials', '/api/admin/stats', '/api/admin/clear-log',
    '/api/admin/settings', '/api/video-history', '/api/list-images',
    '/api/upload-image', '/api/delete-asset', '/api/delete-video',
    '/api/migrate-asset', '/api/repair-images', '/api/proxy-download',
}

def _viewer_public_enabled():
    """Return True if the owner has toggled the customer menu to public."""
    if not DATABASE_URL:
        return True  # local dev: treat as public
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT value FROM site_settings WHERE key = 'viewer_public'")
        row = cur.fetchone()
        cur.close()
        return bool(row and row[0] == 'true')
    except Exception:
        return False
    finally:
        if conn:
            conn.close()

@app.before_request
def _auth_gate():
    """Enforce server-side access control on every request."""
    path = request.path

    # 1) Auth endpoints + OPTIONS preflight are always open
    if path in PUBLIC_PATHS or request.method == 'OPTIONS':
        return None

    # 2) Static assets and page HTML are always open (the lock overlay sits on top)
    #    .ttf, export-utils.js, favicon, /Images/, /user-images/, manuals
    if (path.endswith('.ttf') or path == '/export-utils.js' or
            path == '/favicon.ico' or path.startswith('/Images/') or
            path.startswith('/user-images/') or
            path in ('/manual-en.html', '/manual-es.html')):
        return None

    # 3) From here on, only /api/* and the two page routes need examination.
    is_api = path.startswith('/api/')

    # 4) Whitelisted IP => full access to everything
    if _is_whitelisted(_get_client_ip()):
        return None

    # 5) NOT whitelisted. Decide what (if anything) they may see.
    #    Hard-protected API paths are never public:
    if path in PROTECTED_API_PATHS:
        return jsonify({'error': 'Unauthorized'}), 403

    #    The menu READ endpoints (/api/menu GET, /api/backup GET) are public
    #    ONLY when the owner has enabled viewer_public. Note: credentials have
    #    already been scrubbed from these responses by _strip_credentials().
    if path in ('/api/menu', '/api/backup'):
        if request.method == 'GET' and _viewer_public_enabled():
            return None
        # Viewer locked, or a write attempt by a stranger — block.
        return jsonify({'error': 'Unauthorized'}), 403

    #    AI generation/test endpoints (POST /api/ai/*) — require auth.
    #    All other /api/* not explicitly listed above — require auth.
    if is_api:
        return jsonify({'error': 'Unauthorized'}), 403

    # 6) Non-API page routes (/, /menu, /admin) — always serve the HTML so the
    #    lock overlay can render. The admin page route additionally redirects
    #    non-whitelisted IPs itself.
    return None

@app.route("/")
def index():
    if not os.path.exists("index.html"):
        return "Critical Error: index.html not found.", 500
    response = send_from_directory(".", "index.html")
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

@app.route('/export-utils.js')
def serve_export_utils():
    return send_from_directory('.', 'export-utils.js')

@app.route('/<path:filename>.ttf')
def serve_fonts(filename):
    # Fix: Use absolute path for font serving to prevent 404s on deep routes
    font_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(font_dir, filename + '.ttf')

@app.route("/api/menu", methods=["GET"])
def get_menu():
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            # Explicitly query the 'main' record and 'canvas_json' column
            cur.execute("SELECT canvas_json FROM sessions WHERE id = 'main'")
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                # SECURITY: never expose aiCredentials via the menu endpoint —
                # the public viewer reads /api/menu too. Scrub them here.
                return jsonify(_strip_credentials(row[0]))
        return jsonify(DEFAULT_MENU_DATA)
    except Exception as e:
        print(f"get_menu ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/backup", methods=["POST"])
def save_backup():
    if request.content_length and request.content_length > 5_000_000:
        return jsonify({"error": "Payload too large"}), 413
    data = request.json
    if not data or not validate_schema(data):
        return jsonify({"error": "Invalid payload"}), 400
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sessions (id, canvas_json, updated_at)
            VALUES ('backup', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                canvas_json = EXCLUDED.canvas_json,
                updated_at = CURRENT_TIMESTAMP
        """, (json.dumps(data),))
        conn.commit()
        return jsonify({"status": "backup_saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except Exception:
            pass

@app.route("/api/backup", methods=["GET"])
def get_backup():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT canvas_json, updated_at FROM sessions WHERE id = 'backup'")
        row = cur.fetchone()
        if row:
            data = row[0]
            # Parse stringified JSON just like get_menu if necessary
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass
            return jsonify({"data": _strip_credentials(data), "updated_at": str(row[1])}), 200
        return jsonify({"data": None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except Exception:
            pass

@app.route("/api/menu", methods=["POST"])
def save_menu():
    if request.content_length and request.content_length > 5_000_000:
        return jsonify({"error": "Payload too large"}), 413
    data = request.json
    if not data or not validate_schema(data):
        return jsonify({"error": "Invalid schema"}), 400
    
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        # UPSERT logic using 'canvas_json' and id='main'
        cur.execute("""
            INSERT INTO sessions (id, canvas_json, updated_at) 
            VALUES ('main', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET 
                canvas_json = EXCLUDED.canvas_json,
                updated_at = CURRENT_TIMESTAMP
        """, (json.dumps(data),))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"save_menu ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/migrate-asset", methods=["POST"])
def migrate_asset():
    conn = None
    try:
        if not DATABASE_URL: return jsonify({"error": "No DB"}), 500
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT canvas_json FROM sessions WHERE id = 'main'")
        row = cur.fetchone()
        if not row: return jsonify({"status": "no_data_to_migrate"})
        menu_json = row[0]
        elements = menu_json.get("elements", [])
        modified = False
        for el in elements:
            if el.get("type") == "image" and "Asset2_1.png" in (el.get("src") or ""):
                el["src"] = el["src"].replace("Asset2_1.png", "Asset2.png")
                modified = True
        if modified:
            cur.execute("UPDATE sessions SET canvas_json = %s, updated_at = CURRENT_TIMESTAMP WHERE id = 'main'", (json.dumps(menu_json),))
            conn.commit()
        cur.close()
        return jsonify({"status": "migrated" if modified else "not_needed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route("/api/repair-images", methods=["POST"])
def repair_images():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Use 'canvas_json' and id='main' record
        cur.execute("SELECT canvas_json FROM sessions WHERE id = 'main'")
        row = cur.fetchone()
        if not row: return jsonify({"error": "No session found"}), 404
        data = row['canvas_json']
        fixed = 0
        for el in data.get("elements", []):
            src = el.get("src", "")
            if src and not src.startswith("http") and not src.startswith("data:"):
                el["src"] = ""; el["assetId"] = ""; fixed += 1
        # UPSERT logic using 'canvas_json' and id='main'
        cur.execute("""
            INSERT INTO sessions (id, canvas_json, updated_at) 
            VALUES ('main', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET 
                canvas_json = EXCLUDED.canvas_json,
                updated_at = CURRENT_TIMESTAMP
        """, (json.dumps(data),))
        conn.commit()
        cur.close(); conn.close()
        return jsonify({"status": "ok", "fixed": fixed}), 200
    except Exception as e:
        print(f"repair_images ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete-asset/<filename>", methods=["DELETE"])
def delete_asset(filename):
    try:
        filename = os.path.basename(filename)
        if filename in PROTECTED_ASSETS: return jsonify({"error": "Cannot delete template asset"}), 403
        f1 = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(f1):
            os.remove(f1)
            return jsonify({"status": "deleted"})
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/list-images", methods=["GET"])
def list_images():
    try:
        files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        return jsonify({"images": [{"filename": f, "url": f"/Images/{f}"} for f in sorted(files)]}), 200
    except Exception as e:
        return jsonify({"images": [], "error": str(e)}), 500

@app.route("/Images/<string:filename>")
def serve_root_image(filename):
    response = send_from_directory(IMAGES_DIR, filename)
    response.headers["Cache-Control"] = "max-age=604800, public"
    return response

@app.route("/user-images/<string:filename>")
def serve_user_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/menu')
def customer_viewer():
    response = send_from_directory('.', 'viewer.html')
    response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response

@app.route("/api/ai/test-cloudinary", methods=["POST"])
def test_cloudinary():
    try:
        data = request.json or {}
        cloud_name = data.get("cloud_name", "")
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        if not all([cloud_name, api_key, api_secret]): return jsonify({"error": "Missing credentials"}), 400
        timestamp = int(time.time())
        sig = cloudinary_sign({"timestamp": timestamp}, api_secret)
        url = f"https://api.cloudinary.com/v1_1/{cloud_name}/resources/image?timestamp={timestamp}&api_key={api_key}&signature={sig}"
        client = _http()
        resp = client.get(url)
        if resp.status_code in (200, 401): return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid credentials"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/test-stability", methods=["POST"])
def test_stability():
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        if not api_key: return jsonify({"error": "Missing API key"}), 400
        client = _http()
        resp = client.get("https://api.stability.ai/v1/user/account", headers={"Authorization": f"Bearer {api_key}"})
        if resp.status_code == 200: return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid API key"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/test-kling", methods=["POST"])
def test_kling():
    try:
        data = request.json or {}
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        if not all([api_key, api_secret]): return jsonify({"error": "Missing credentials"}), 400
        token = generate_kling_token(api_key, api_secret)
        client = _http()
        test_url = "https://api.klingai.com/v1/videos/text2video?pageNum=1&pageSize=1"
        resp = client.get(test_url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code in (200, 401): return jsonify({"status": "ok"})
        return jsonify({"error": "Invalid credentials"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/enhance-prompt", methods=["POST"])
def enhance_prompt():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "")
        prompt_type = data.get("type", "image")
        if not prompt: return jsonify({"error": "Prompt is required"}), 400
        modifiers = "professional food photography, soft natural lighting, shallow depth of field, 85mm lens, restaurant-quality presentation, high resolution, appetizing composition" if prompt_type == "image" else "cinematic food video, slow motion, professional lighting, 4K quality, appetizing presentation, smooth camera movement, broadcast quality"
        # Check if the prompt already contains the first identifiable part of the modifiers string
        check_phrase = "professional food photography" if prompt_type == "image" else "cinematic food video"
        enhanced = prompt if check_phrase in prompt.lower() else f"{prompt}. {modifiers}"
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

            # Ensure raw base64 only (no data URI prefix)
            raw_b64 = reference_image_b64
            if ',' in raw_b64:
                raw_b64 = raw_b64.split(',', 1)[1]
            # Decode to raw bytes for proper multipart binary upload
            try:
                image_bytes = base64.b64decode(raw_b64)
            except Exception as decode_err:
                return jsonify({'error': f'Invalid base64 for reference image: {decode_err}'}), 400
            c_ts = int(time.time())
            c_sig = cloudinary_sign({"folder": "nymk_ai_refs", "timestamp": c_ts}, c_secret)
            c_url = f"https://api.cloudinary.com/v1_1/{c_name}/image/upload"

            c_fields = {
                "api_key": c_key,
                "timestamp": c_ts,
                "signature": c_sig,
                "folder": "nymk_ai_refs"
            }

            c_files = {"file": ("reference.png", image_bytes, "image/png")}
            for k, v in c_fields.items():
                c_files[k] = (None, str(v))

            c_resp = client.post(c_url, files=c_files, timeout=60)
            if c_resp.status_code not in (200, 201):
                return jsonify({"error": f"Cloudinary upload failed for reference image: {c_resp.text}"}), 400
            
            public_url = c_resp.json().get("secure_url")
            if not public_url:
                return jsonify({"error": "Failed to get public URL from Cloudinary"}), 400

            # 3. Use the public URL in the Kling payload
            payload["image"] = public_url
        
        # DEBUG: Print payload to console (visible in Railway logs)
        print(f"DEBUG: Kling Payload: {json.dumps({k: (v[:50] + '...') if k == 'image' and isinstance(v, str) and len(v) > 50 else v for k, v in payload.items()})}")

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

# Video behavior logic restored — persistence for AI session pipeline

@app.route("/api/video-history", methods=["GET"])
def get_video_history():
    conn = None
    try:
        if not DATABASE_URL:
            return jsonify({"hero": [], "left": [], "right": []})
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("""
            SELECT slot, url FROM video_history
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        result = {"hero": [], "left": [], "right": []}
        seen = {"hero": set(), "left": set(), "right": set()}
        for slot, url in rows:
            if slot in result and url not in seen[slot] and len(result[slot]) < 5:
                result[slot].append(url)
                seen[slot].add(url)
        cur.close()
        return jsonify(result)
    except Exception as e:
        print(f"get_video_history ERROR: {e}", flush=True)
        return jsonify({"hero": [], "left": [], "right": []})
    finally:
        if conn:
            conn.close()

@app.route("/api/video-history", methods=["POST"])
def save_video_history():
    conn = None
    try:
        data = request.json or {}
        slot = data.get("slot", "")
        url = data.get("url", "")
        if slot not in ("hero", "left", "right") or not url:
            return jsonify({"error": "Invalid slot or url"}), 400
        if not DATABASE_URL:
            return jsonify({"status": "no_db"}), 200
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        # Avoid duplicate consecutive saves of the same URL to the same slot
        # Correctly only checks the single most recent record for this slot
        cur.execute("""
            INSERT INTO video_history (slot, url)
            SELECT %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM (
                    SELECT url FROM video_history 
                    WHERE slot = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ) last_entry 
                WHERE last_entry.url = %s
            )
        """, (slot, url, slot, url))
        conn.commit()
        cur.close()
        return jsonify({"status": "saved"})
    except Exception as e:
        print(f"save_video_history ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/image-history", methods=["GET"])
def get_image_history():
    conn = None
    try:
        if not DATABASE_URL:
            return jsonify({"images": []})
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT canvas_json FROM sessions WHERE id = 'main'")
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify({"images": []})
        data = row[0]
        assets = data.get("assets", [])
        ai_images = [
            {"id": a.get("id"), "name": a.get("name", "AI Image"),
             "url": (a.get("storage") or {}).get("originalUrl", "")}
            for a in assets
            if a.get("id", "").startswith("asset_ai") or "AI" in a.get("name", "")
        ]
        return jsonify({"images": ai_images[-20:]})
    except Exception as e:
        return jsonify({"images": [], "error": str(e)})
    finally:
        if conn:
            conn.close()

@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    try:
        data = request.json or {}
        file_b64 = data.get("data", "")
        filename = data.get("filename", "")
        creds = data.get("credentials", {})
        # NOTE: This endpoint uses camelCase keys (cloudName, cloudKey, cloudSecret)
        # matching the primary docV2.aiCredentials schema used in index.html:saveAiCredentials().
        cloud_name = creds.get("cloudName", "")
        api_key = creds.get("cloudKey", "")
        api_secret = creds.get("cloudSecret", "")

        if not file_b64:
            return jsonify({"error": "Missing file data"}), 400

        import base64 as _b64_mod
        try:
            raw_b64 = file_b64.split(",")[1] if "," in file_b64 else file_b64
            raw_bytes = _b64_mod.b64decode(raw_b64)
        except Exception:
            return jsonify({"error": "Invalid base64 data"}), 400

        if all([cloud_name, api_key, api_secret]):
            # Upload to Cloudinary
            client = _http()
            if not client:
                return jsonify({"error": "No HTTP client available"}), 500

            timestamp = int(time.time())
            params = {"folder": "nymk_ai", "timestamp": timestamp}
            upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
            sig = cloudinary_sign(params, api_secret)

            upload_fields = dict(params)
            upload_fields["api_key"] = api_key
            upload_fields["signature"] = sig

            upload_files = {"file": (filename or "upload.png", raw_bytes, "image/png")}
            for k, v in upload_fields.items():
                upload_files[k] = (None, str(v))

            resp = client.post(upload_url, files=upload_files, timeout=60)
            if resp.status_code in (200, 201):
                return jsonify({"status": "ok", "url": resp.json().get("secure_url", "")})
            return jsonify({"error": f"Cloudinary upload failed — status {resp.status_code if resp else 'no response'}"}), 400
        else:
            return jsonify({"error": "Cloudinary credentials required to save images permanently. Fill in your credentials in AI Studio → Credentials."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/cloudinary-upload", methods=["POST"])
def cloudinary_upload():
    try:
        data = request.json or {}
        file_b64 = data.get("file_b64", "")
        file_url = data.get("file_url", "")
        file_type = data.get("file_type", "image")
        creds = data.get("credentials", {})
        # NOTE: This endpoint uses snake_case keys (cloud_name, api_key, api_secret) 
        # matching the specialized AI upload handlers in index.html. 
        # Cross-reference with /api/upload-image which uses camelCase.
        cloud_name = creds.get("cloud_name", "")
        api_key = creds.get("api_key", "")
        api_secret = creds.get("api_secret", "")
        
        if not all([cloud_name, api_key, api_secret]) or (not file_b64 and not file_url):
            return jsonify({"error": "Missing file or credentials"}), 400



        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client available"}), 500

        timestamp = int(time.time())
        
        # Step 1 & 2: Build params dict for both signing AND sending
        if file_type == "video":
            params = {"folder": "nymk_ai", "timestamp": timestamp}
            upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/video/upload"
        else:
            params = {"folder": "nymk_ai", "timestamp": timestamp}
            upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
        
        # Sign the exact params dict
        sig = cloudinary_sign(params, api_secret)
        
        # Step 3 & 4: Build upload_fields from the same params dict
        upload_fields = dict(params)
        upload_fields["api_key"] = api_key
        upload_fields["signature"] = sig
        
        # Resolve raw bytes from B64 or URL
        import base64 as _b64_mod
        if file_url:
            # Fetch the URL bytes directly
            u_resp = client.get(file_url, timeout=180)
            if u_resp.status_code != 200:
                return jsonify({"error": f"Failed to fetch source file from URL: {file_url}"}), 400
            raw_bytes = u_resp.content
        else:
            # Decode base64
            try:
                if "," in file_b64:
                    file_b64 = file_b64.split(",")[1]
                raw_bytes = _b64_mod.b64decode(file_b64)
            except Exception:
                return jsonify({"error": "Invalid base64 data"}), 400

        # Build upload_files dictionary
        if file_type == "video":
            upload_files = {"file": ("upload.mp4", raw_bytes, "video/mp4")}
        else:
            upload_files = {"file": ("upload.png", raw_bytes, "image/png")}
        
        for k, v in upload_fields.items():
            upload_files[k] = (None, str(v))
        
        timeout_val = 180 if file_type == "video" else 60
        resp = client.post(upload_url, files=upload_files, timeout=timeout_val)
        if resp.status_code in (200, 201):
            result = resp.json()
            return jsonify({"url": result.get("secure_url", "")})
        return jsonify({"error": f"Cloudinary upload failed — status {resp.status_code if resp else 'no response'}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/proxy-download", methods=["POST"])
def proxy_download():
    try:
        data = request.json or {}
        url = data.get("url", "").strip()
        if not url or not url.startswith("http"):
            return jsonify({"error": "Invalid URL"}), 400
        client = _http()
        if not client:
            return jsonify({"error": "No HTTP client"}), 500
        resp = client.get(url, timeout=60)
        if resp.status_code != 200:
            return jsonify({"error": "Failed to fetch file"}), 400
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        from flask import Response
        return Response(
            resp.content,
            status=200,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": "attachment"
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete-video", methods=["DELETE"])
def delete_video():
    conn = None
    try:
        data = request.json or {}
        slot = data.get("slot", "")
        url = data.get("url", "")
        if slot not in ("hero", "left", "right") or not url:
            return jsonify({"error": "Invalid slot or url"}), 400
        if not DATABASE_URL:
            return jsonify({"status": "no_db"}), 200
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM video_history WHERE slot = %s AND url = %s",
            (slot, url)
        )
        conn.commit()
        cur.close()
        return jsonify({"status": "deleted"})
    except Exception as e:
        print(f"delete_video ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/manual-en.html')
def manual_en():
    return send_from_directory('.', 'manual-en.html')

@app.route('/manual-es.html')
def manual_es():
    return send_from_directory('.', 'manual-es.html')

# ─── ACCESS CONTROL HELPERS ───────────────────────────────────────────────────

def _get_client_ip():
    """Return real client IP, accounting for Railway's reverse proxy."""
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def _is_whitelisted(ip):
    """Return True if this IP is in ip_whitelist."""
    if not DATABASE_URL:
        return True  # No DB = open (local dev)
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM ip_whitelist WHERE ip = %s", (ip,))
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        if conn:
            conn.close()

# ─── AI CREDENTIALS STORAGE (separate from menu document) ─────────────────────
# Credentials live in site_settings under key='ai_credentials' as a JSON string.
# They are NEVER stored inside the menu document (canvas_json), so they are never
# served to the public viewer and never overwritten by a menu save().

CRED_FIELDS = ('cloudName', 'cloudKey', 'cloudSecret',
               'klingKey', 'klingSecret', 'stabilityKey')

_EMPTY_CREDS = {f: '' for f in CRED_FIELDS}

def get_ai_credentials():
    """Return the stored AI credentials dict (empty strings if none/unavailable)."""
    if not DATABASE_URL:
        return dict(_EMPTY_CREDS)
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT value FROM site_settings WHERE key = 'ai_credentials'")
        row = cur.fetchone()
        cur.close()
        if not row:
            return dict(_EMPTY_CREDS)
        try:
            stored = json.loads(row[0]) if row[0] else {}
        except Exception:
            stored = {}
        # Merge against known fields so callers always get the full schema
        merged = dict(_EMPTY_CREDS)
        for f in CRED_FIELDS:
            merged[f] = (stored.get(f) or '').strip()
        return merged
    except Exception:
        return dict(_EMPTY_CREDS)
    finally:
        if conn:
            conn.close()

def save_ai_credentials(creds):
    """Persist AI credentials dict to site_settings. Returns True on success."""
    if not DATABASE_URL:
        return True
    conn = None
    try:
        # Sanitize: keep only known fields, trim, reject non-strings
        clean = {}
        for f in CRED_FIELDS:
            v = creds.get(f, '')
            clean[f] = str(v).strip() if v is not None else ''
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO site_settings (key, value, updated_at)
               VALUES ('ai_credentials', %s, CURRENT_TIMESTAMP)
               ON CONFLICT (key) DO UPDATE
               SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP""",
            (json.dumps(clean),)
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"save_ai_credentials ERROR: {e}", flush=True)
        return False
    finally:
        if conn:
            conn.close()

def _strip_credentials(doc):
    """Recursively remove aiCredentials from a menu document (or any dict).
    Mutates a copy and returns it. Used before serving /api/menu and /api/backup."""
    if isinstance(doc, dict):
        d = dict(doc)
        if 'aiCredentials' in d:
            d['aiCredentials'] = dict(_EMPTY_CREDS)
        return d
    return doc

# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route('/api/auth/check', methods=['POST'])
def auth_check():
    """Returns whether this IP is already whitelisted.
    If viewer_public=true and page is /menu, always returns unlocked."""
    ip = _get_client_ip()
    data = request.get_json(force=True, silent=True) or {}
    page = data.get('page', '/')

    # Check viewer_public setting for /menu page
    if page == '/menu' and DATABASE_URL:
        conn = None
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            cur.execute("SELECT value FROM site_settings WHERE key = 'viewer_public'")
            row = cur.fetchone()
            if row and row[0] == 'true':
                return jsonify({'unlocked': True, 'public': True})
        except Exception:
            pass
        finally:
            if conn:
                conn.close()

    return jsonify({'unlocked': _is_whitelisted(ip)})

@app.route('/api/auth/unlock', methods=['POST'])
def auth_unlock():
    """Verifies password and, if correct, adds IP to whitelist."""
    ip = _get_client_ip()
    data = request.get_json(force=True, silent=True) or {}
    password = data.get('password', '')
    page = data.get('page', '/')
    ua = request.headers.get('User-Agent', '')[:512]
    conn = None
    try:
        if password == SITE_PASSWORD:
            if DATABASE_URL:
                conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO ip_whitelist (ip) VALUES (%s) ON CONFLICT (ip) DO NOTHING",
                    (ip,)
                )
                cur.execute(
                    "INSERT INTO access_log (ip, page, event, user_agent) VALUES (%s, %s, %s, %s)",
                    (ip, page, 'unlock_success', ua)
                )
                conn.commit()
                cur.close()
            return jsonify({'success': True})
        else:
            if DATABASE_URL:
                conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO access_log (ip, page, event, user_agent) VALUES (%s, %s, %s, %s)",
                    (ip, page, 'unlock_fail', ua)
                )
                conn.commit()
                cur.close()
            return jsonify({'success': False, 'error': 'Incorrect password'}), 401
    except Exception as e:
        print(f"auth_unlock ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/auth/log', methods=['POST'])
def auth_log():
    """Logs a visit or leave event for analytics."""
    ip = _get_client_ip()
    data = request.get_json(force=True, silent=True) or {}
    page = data.get('page', '/')
    event = data.get('event', 'visit')
    duration = data.get('duration_seconds')
    ua = request.headers.get('User-Agent', '')[:512]
    if event not in ('visit', 'leave'):
        return jsonify({'error': 'Invalid event'}), 400
    conn = None
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO access_log (ip, page, event, user_agent, duration_seconds) VALUES (%s, %s, %s, %s, %s)",
                (ip, page, event, ua, duration)
            )
            conn.commit()
            cur.close()
        return jsonify({'status': 'logged'})
    except Exception as e:
        print(f"auth_log ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# ─── ADMIN ROUTES ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_page():
    """Serves admin.html — only to whitelisted IPs."""
    ip = _get_client_ip()
    if not _is_whitelisted(ip):
        # Redirect to home which will show the lock page
        from flask import redirect
        return redirect('/')
    if not os.path.exists('admin.html'):
        return 'Admin page not found.', 404
    response = send_from_directory('.', 'admin.html')
    response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    """Returns full analytics data — only to whitelisted IPs."""
    ip = _get_client_ip()
    if not _is_whitelisted(ip):
        return jsonify({'error': 'Unauthorized'}), 403
    conn = None
    try:
        if not DATABASE_URL:
            return jsonify({'whitelist': [], 'log': [], 'summary': {}})
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()

        # Whitelist with visit counts
        cur.execute("""
            SELECT w.ip, w.unlocked_at,
                   COUNT(l.id) FILTER (WHERE l.event = 'visit') AS visit_count,
                   MAX(l.created_at) AS last_seen
            FROM ip_whitelist w
            LEFT JOIN access_log l ON l.ip = w.ip
            GROUP BY w.ip, w.unlocked_at
            ORDER BY w.unlocked_at DESC
        """)
        whitelist = []
        for row in cur.fetchall():
            whitelist.append({
                'ip': row[0],
                'unlocked_at': str(row[1]),
                'visit_count': row[2] or 0,
                'last_seen': str(row[3]) if row[3] else None
            })

        # Full access log (last 500)
        cur.execute("""
            SELECT id, ip, page, event, user_agent, duration_seconds, created_at
            FROM access_log
            ORDER BY created_at DESC
            LIMIT 500
        """)
        log = []
        for row in cur.fetchall():
            log.append({
                'id': row[0],
                'ip': row[1],
                'page': row[2],
                'event': row[3],
                'user_agent': row[4],
                'duration_seconds': row[5],
                'created_at': str(row[6])
            })

        # Summary stats
        cur.execute("SELECT COUNT(*) FROM ip_whitelist")
        total_unlocked = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT ip) FROM access_log")
        unique_ips = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM access_log WHERE event = 'page_view'")
        total_page_views = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM access_log WHERE event = 'visit'")
        total_visits = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM access_log WHERE event = 'unlock_fail'")
        failed_attempts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM access_log WHERE event = 'unlock_success'")
        successful_unlocks = cur.fetchone()[0]

        cur.close()
        return jsonify({
            'whitelist': whitelist,
            'log': log,
            'summary': {
                'total_unlocked_ips': total_unlocked,
                'unique_ips_seen': unique_ips,
                'total_page_views': total_page_views,
                'total_visits': total_visits,
                'failed_attempts': failed_attempts,
                'successful_unlocks': successful_unlocks
            }
        })
    except Exception as e:
        print(f"admin_stats ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/auth/page-view', methods=['POST'])
def auth_page_view():
    """Logs a page_view event for ANY real visitor — including silent ones
    who never attempt to unlock. Called immediately on page load.
    Bots are detected via User-Agent and silently ignored."""

    # Known bot / crawler signatures — case-insensitive substring match
    BOT_SIGNATURES = [
        # Search engines
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'sogou', 'exabot', 'facebot', 'ia_archiver',
        'applebot', 'msnbot', 'teoma', 'ask jeeves',
        # Social media previewers
        'facebookexternalhit', 'twitterbot', 'linkedinbot', 'whatsapp',
        'slackbot', 'discordbot', 'telegrambot', 'pinterest',
        'vkshare', 'xing-contenttabreceiver',
        # SEO / analytics tools
        'semrushbot', 'ahrefsbot', 'mj12bot', 'dotbot', 'rogerbot',
        'screaming frog', 'sitebulb', 'seokicks', 'serpstatbot',
        # Security / uptime scanners
        'zgrab', 'masscan', 'nmap', 'nikto', 'sqlmap', 'curl/', 'wget/',
        'python-requests', 'python-urllib', 'go-http-client',
        'java/', 'ruby/', 'perl/', 'libwww-perl',
        # Headless / automation (non-user)
        'headlesschrome', 'phantomjs', 'selenium',
        # Generic bot markers
        'bot', 'crawler', 'spider', 'scraper', 'scan', 'fetch',
        'archiver', 'checker', 'monitor', 'validator', 'preview',
    ]

    ua = request.headers.get('User-Agent', '').lower()

    # Empty UA is also a strong bot signal
    if not ua or any(sig in ua for sig in BOT_SIGNATURES):
        return jsonify({'status': 'ignored'}), 200

    ip = _get_client_ip()
    data = request.get_json(force=True, silent=True) or {}
    page = data.get('page', '/')
    ua_raw = request.headers.get('User-Agent', '')[:512]
    conn = None
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO access_log (ip, page, event, user_agent) VALUES (%s, %s, %s, %s)",
                (ip, page, 'page_view', ua_raw)
            )
            conn.commit()
            cur.close()
        return jsonify({'status': 'logged'})
    except Exception as e:
        print(f"auth_page_view ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ─── ADMIN SETTINGS ROUTES ──────────────────────────────────────────────────

@app.route('/api/admin/clear-log', methods=['POST'])
def admin_clear_log():
    """Deletes all rows from access_log. Whitelisted IPs only."""
    ip = _get_client_ip()
    if not _is_whitelisted(ip):
        return jsonify({'error': 'Unauthorized'}), 403
    conn = None
    try:
        if not DATABASE_URL:
            return jsonify({'deleted': 0})
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("DELETE FROM access_log")
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        return jsonify({'status': 'cleared', 'deleted': deleted})
    except Exception as e:
        print(f"admin_clear_log ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/settings', methods=['GET'])
def admin_settings_get():
    """Returns all site settings. Whitelisted IPs only."""
    ip = _get_client_ip()
    if not _is_whitelisted(ip):
        return jsonify({'error': 'Unauthorized'}), 403
    conn = None
    try:
        if not DATABASE_URL:
            return jsonify({'viewer_public': 'false'})
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM site_settings")
        settings = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()
        return jsonify(settings)
    except Exception as e:
        print(f"admin_settings_get ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/settings', methods=['POST'])
def admin_settings_post():
    """Updates a site setting. Whitelisted IPs only."""
    ip = _get_client_ip()
    if not _is_whitelisted(ip):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json or {}
    # Only allow known settings keys
    allowed_keys = {'viewer_public'}
    conn = None
    try:
        if not DATABASE_URL:
            return jsonify({'status': 'ok (no-db)'})
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        for key, value in data.items():
            if key not in allowed_keys:
                continue
            # Sanitize: only 'true' or 'false' for boolean settings
            safe_value = 'true' if str(value).lower() in ('true', '1', 'yes') else 'false'
            cur.execute(
                """INSERT INTO site_settings (key, value, updated_at)
                   VALUES (%s, %s, CURRENT_TIMESTAMP)
                   ON CONFLICT (key) DO UPDATE
                   SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP""",
                (key, safe_value)
            )
        conn.commit()
        cur.close()
        return jsonify({'status': 'updated'})
    except Exception as e:
        print(f"admin_settings_post ERROR: {e}", flush=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# ─── AI CREDENTIALS ENDPOINTS (whitelisted IPs only) ──────────────────────────
# These are the ONLY endpoints that serve real credential values to the browser.
# The auth gate (before_request) blocks non-whitelisted IPs from reaching them.

@app.route('/api/credentials', methods=['GET'])
def get_credentials():
    """Return AI credentials — whitelisted IPs only (enforced by auth gate)."""
    return jsonify(get_ai_credentials())

@app.route('/api/credentials', methods=['POST'])
def post_credentials():
    """Save AI credentials — whitelisted IPs only (enforced by auth gate)."""
    data = request.json or {}
    ok = save_ai_credentials(data)
    if ok:
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Failed to save credentials'}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
