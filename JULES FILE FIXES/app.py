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
DEFAULT_MENU_DATA_JSON = '''
{"version": 2, "elements": [{"id": "bg_001", "type": "image", "src": "/Images/Asset2.png", "assetId": "asset_007", "x": 0, "y": 0, "width": 908.44, "height": 1336.02, "zIndex": 0, "opacity": 1, "rotation": 0, "visible": true, "locked": true, "layerRole": "background"}, {"id": "txt_0", "type": "text", "text": "SANDWICHES", "x": 631.39208984375, "y": 550.313720703125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_1", "type": "text", "text": "MAIN ENTREES", "x": 494.3760986328125, "y": 133.55673217773438, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_2", "type": "text", "text": "A LA CARTE", "x": 382.0440979003906, "y": 549.32373046875, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_3", "type": "text", "text": "WINGS", "x": 417.1890869140625, "y": 788.57373046875, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_4", "type": "text", "text": "Catfish", "x": 407.08349609375, "y": 189.51132202148438, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_5", "type": "text", "text": "$21.99", "x": 749.04736328125, "y": 189.51132202148438, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_6", "type": "text", "text": "$22.99", "x": 749.04736328125, "y": 216.16598510742188, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_7", "type": "text", "text": "$19.99", "x": 749.04736328125, "y": 241.38510131835938, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_8", "type": "text", "text": "$15.99", "x": 749.04736328125, "y": 268.5900573730469, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_9", "type": "text", "text": "$17.99", "x": 749.04736328125, "y": 294.9576110839844, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_10", "type": "text", "text": "$16.99", "x": 749.04736328125, "y": 321.3251647949219, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_11", "type": "text", "text": "$12.99", "x": 749.04736328125, "y": 346.8313293457031, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_12", "type": "text", "text": "$29.99", "x": 749.04736328125, "y": 372.1460876464844, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_13", "type": "text", "text": "$22.99", "x": 749.04736328125, "y": 398.7050476074219, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_14", "type": "text", "text": "Turkey Chops", "x": 407.0835266113281, "y": 216.11813354492188, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_15", "type": "text", "text": "Shrimp Plate", "x": 407.0835266113281, "y": 242.96420288085938, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_16", "type": "text", "text": "Party Wings Plate (6)", "x": 407.0835266113281, "y": 269.9777526855469, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_17", "type": "text", "text": "Fried Chicken Plate - White Meat", "x": 407.0835266113281, "y": 294.9336242675781, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_18", "type": "text", "text": "Fried Chicken Plate - Dark Meat", "x": 407.0835266113281, "y": 320.8705139160156, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_19", "type": "text", "text": "Veggie Plate", "x": 407.0835266113281, "y": 346.8074035644531, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_20", "type": "text", "text": "Oxtails w/Rice & Gravy", "x": 407.0835266113281, "y": 373.7492370605469, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_21", "type": "text", "text": "Turkey WIngs w/Rice & Gravy", "x": 407.0835266113281, "y": 398.7051086425781, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_22", "type": "text", "text": "Catfish 3 pieces", "x": 367.095703125, "y": 607.5958251953125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_23", "type": "text", "text": "$5.50", "x": 538.625244140625, "y": 588.5143432617188, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_24", "type": "text", "text": "Shrimp Po’ Boy", "x": 604.43310546875, "y": 643.661865234375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_25", "type": "text", "text": "Catfish Po’ Boy", "x": 604.43310546875, "y": 668.5978393554688, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_26", "type": "text", "text": "$17.99", "x": 814.455078125, "y": 670.8505859375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_27", "type": "text", "text": "$16.99", "x": 814.455078125, "y": 645.902587890625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_28", "type": "text", "text": "DESSERTS", "x": 653.3687133789062, "y": 965.841064453125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_29", "type": "text", "text": "Peach Cobbler", "x": 603.77880859375, "y": 1006.7, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_30", "type": "text", "text": "Banana Pudding", "x": 603.77880859375, "y": 1031.7, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_31", "type": "text", "text": "Coffee Cake", "x": 603.77880859375, "y": 1056.7, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_32", "type": "text", "text": "$6.00", "x": 826.455078125, "y": 1006.7, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_33", "type": "text", "text": "$6.00", "x": 826.455078125, "y": 1031.7, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_34", "type": "text", "text": "$6.00", "x": 826.455078125, "y": 1056.7, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_35", "type": "text", "text": "SIDES", "x": 682.62841796875, "y": 738.2111206054688, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_36", "type": "text", "text": "Candied Yams", "x": 603.77880859375, "y": 796.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_37", "type": "text", "text": " ", "x": 728.1184692382812, "y": 796.0264282226562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_38", "type": "text", "text": "Cabbage", "x": 738.4916381835938, "y": 796.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_39", "type": "text", "text": "Mac N Cheese", "x": 603.77880859375, "y": 821.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_40", "type": "text", "text": " ", "x": 729.1574096679688, "y": 819.6660766601562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_41", "type": "text", "text": "Red Beans & Rice", "x": 738.330078125, "y": 821.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_42", "type": "text", "text": "Rice & Gravy", "x": 603.77880859375, "y": 846.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_43", "type": "text", "text": "Collard Greens", "x": 737.5737915039062, "y": 846.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_44", "type": "text", "text": "French Fries", "x": 737.57373046875, "y": 871.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_45", "type": "text", "text": "French Fries (Lrg)", "x": 604.5772705078125, "y": 896.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_46", "type": "text", "text": "Potato Salad", "x": 603.77880859375, "y": 871.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_47", "type": "text", "text": "$7.99", "x": 826.455078125, "y": 896.0, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_48", "type": "text", "text": "($3.99 each)", "x": 686.66552734375, "y": 776.0515747070312, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 14.93958854675293, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_49", "type": "text", "text": "$8.49", "x": 538.6328125, "y": 663.0020141601562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_50", "type": "text", "text": "$3.00", "x": 538.6328125, "y": 699.8838500976562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_51", "type": "text", "text": "$3.50", "x": 538.6328125, "y": 737.01806640625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_52", "type": "text", "text": "$1.00", "x": 538.6328125, "y": 755.8666381835938, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_53", "type": "text", "text": "Canned Soft Drink", "x": 367.8152770996094, "y": 1010.3901977539062, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_54", "type": "text", "text": "Sweet Tea Small", "x": 367.8152770996094, "y": 1028.9283447265625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_55", "type": "text", "text": "Sweet Tea Large", "x": 367.8152770996094, "y": 1047.46630859375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_56", "type": "text", "text": "Lemonade Small", "x": 367.8152770996094, "y": 1066.0042724609375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_57", "type": "text", "text": "Lemonade Large", "x": 367.8152770996094, "y": 1084.542236328125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_58", "type": "text", "text": "Arnold Palmer Sm", "x": 367.8152770996094, "y": 1103.0802001953125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_59", "type": "text", "text": "Arnold Palmer Lrg", "x": 367.8152770996094, "y": 1121.6182861328125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_60", "type": "text", "text": "BEVERAGES", "x": 379.4755859375, "y": 966.032470703125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-regular", "fontSize": 33.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_61", "type": "text", "text": "$1.75", "x": 536.6328125, "y": 1010.4033813476562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_62", "type": "text", "text": "$3.00", "x": 536.6328125, "y": 1029.2908935546875, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_63", "type": "text", "text": "$5.00", "x": 536.6328125, "y": 1048.17822265625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_64", "type": "text", "text": "$3.00", "x": 536.6328125, "y": 1067.0655517578125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_65", "type": "text", "text": "$5.00", "x": 536.6328125, "y": 1085.9530029296875, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_66", "type": "text", "text": "$3.00", "x": 536.6328125, "y": 1104.8404541015625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_67", "type": "text", "text": "$5.00", "x": 536.6328125, "y": 1123.727783203125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_68", "type": "text", "text": "$4.00", "x": 538.6264038085938, "y": 718.066162109375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_69", "type": "text", "text": "$15.99", "x": 529.62353515625, "y": 607.6341552734375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_70", "type": "text", "text": "$15.99", "x": 529.62353515625, "y": 645.0206909179688, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_71", "type": "text", "text": "$13.99", "x": 529.62353515625, "y": 681.4366455078125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_72", "type": "text", "text": "$10.99", "x": 529.62353515625, "y": 625.6091918945312, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_73", "type": "text", "text": "Shrimp 10 pieces", "x": 367.0810546875, "y": 625.6091918945312, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_74", "type": "text", "text": "Turkey Chop(2)", "x": 367.0810546875, "y": 645.0206909179688, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_75", "type": "text", "text": "NYMK Waffle", "x": 367.0810546875, "y": 662.7822265625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_76", "type": "text", "text": "Chicken Wings (3)", "x": 367.095703125, "y": 682.5919189453125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_77", "type": "text", "text": "Leg", "x": 367.095703125, "y": 699.5449829101562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_78", "type": "text", "text": "Wing", "x": 367.095703125, "y": 718.199462890625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_79", "type": "text", "text": "Thigh", "x": 367.095703125, "y": 736.6943969726562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_80", "type": "text", "text": "Cornbread Muffin (1)", "x": 367.09521484375, "y": 754.9776000976562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_81", "type": "text", "text": "6 Piece  -  $10.49", "x": 402.4888000488281, "y": 861.7587890625, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_82", "type": "text", "text": "12 Piece  -  $20.99", "x": 392.4898376464844, "y": 886.622802734375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_83", "type": "text", "text": "18 Piece  -  $30.99", "x": 392.4898376464844, "y": 910.163818359375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_84", "type": "text", "text": "Entrees served with choice of 2 sides", "x": 407.3174133300781, "y": 436.03741455078125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_85", "type": "text", "text": "and cornbread muffin", "x": 407.3174133300781, "y": 454.03741455078125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_86", "type": "text", "text": "Waffles with 3 Fried Whole Wings", "x": 130.4803466796875, "y": 501.2333984375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_87", "type": "text", "text": "(served with tartar sauce, lettuce,", "x": 609.3571166992188, "y": 591.9713745117188, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_88", "type": "text", "text": "tomato, pickles, grilled onions,", "x": 609.3571166992188, "y": 607.973388671875, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_89", "type": "text", "text": "and non spicy cajun sauce)", "x": 609.3571166992188, "y": 623.9754028320312, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_90", "type": "text", "text": "Flavors: Plain, Hot, Honey Hot,", "x": 367.10076904296875, "y": 824.1533813476562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_91", "type": "text", "text": "Lemon Pepper, Sweet Thangs", "x": 367.10076904296875, "y": 842.1533813476562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 16.274938583374023, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_92", "type": "text", "text": "EVERY OTHER WEEKEND", "x": 292.9175109863281, "y": 384.487548828125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 8.702635765075684, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_93", "type": "text", "text": "WEEKENDS ONLY", "x": 301.9205627441406, "y": 410.8623046875, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 8.702635765075684, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_94", "type": "text", "text": "Chicken & Waffles", "x": 147.70309448242188, "y": 477.40283203125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 20.574399948120117, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_95", "type": "text", "text": "$12.99", "x": 249.8251953125, "y": 534.3789672851562, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 23.117069244384766, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_96", "type": "text", "text": "@nym_kitchen", "x": 113.22360229492188, "y": 1245.208740234375, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.0, "color": "#ffffff", "lineHeight": 1.1, "letterSpacing": 0}}, {"id": "txt_97", "type": "text", "text": "Catfish 1 piece", "x": 367.2944030761719, "y": 588.5089111328125, "zIndex": 10, "opacity": 1, "rotation": 0, "visible": true, "locked": false, "layerRole": "content", "style": {"fontFamily": "century-gothic-bold", "fontSize": 17.53, "color": "#000000", "lineHeight": 1.1, "letterSpacing": 0}}]}
'''
DEFAULT_MENU_DATA = json.loads(DEFAULT_MENU_DATA_JSON)

def init_db():
    if not DATABASE_URL:
        return
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
            
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"init_db ERROR: {e}", flush=True)
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
    if data.get("version") == 1: return False
    if not all(isinstance(e, dict) and 'id' in e and 'type' in e for e in data.get('elements', [])): return False
    return True

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
    return send_from_directory('.', filename + '.ttf')

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
                return jsonify(row[0])
        return jsonify(DEFAULT_MENU_DATA)
    except Exception as e:
        print(f"get_menu ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

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

@app.route("/api/menu/reset", methods=["POST"])
def reset_menu():
    conn = None
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            cur.execute("UPDATE sessions SET canvas_json = %s, updated_at = CURRENT_TIMESTAMP WHERE id = 'main'", (json.dumps(DEFAULT_MENU_DATA),))
            conn.commit()
            cur.close()
            return jsonify({"status": "success", "reset": "database"})
        return jsonify({"error": "No database connection"}), 500
    except Exception as e:
        print(f"reset_menu ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

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
        enhanced = prompt if "professional food photography" in prompt.lower() else f"{prompt}. {modifiers}"
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

# Video behavior logic removed — replaced by stateless AI session pipeline

@app.route("/api/ai/cloudinary-upload", methods=["POST"])
def cloudinary_upload():
    try:
        data = request.json or {}
        file_b64 = data.get("file_b64", "")
        file_url = data.get("file_url", "")
        file_type = data.get("file_type", "image")
        creds = data.get("credentials", {})
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
