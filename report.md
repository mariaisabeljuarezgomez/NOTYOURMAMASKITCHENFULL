# Extensive Codebase Review Report

This report consolidates the extensive review of the codebase, focusing on previously identified bugs, inefficiencies, and areas for improvement based on static analysis of `index.html`, `app.py`, `build_app.py`, and `export-utils.js`.

---

## 🔴 Critical Bugs — Risk of Data Loss or Invisible Breakage

### **BUG-C1: `app.py` `/api/render-check` has its own hardcoded asset map**
*   **Location:** `app.py`, `render_check` endpoint
*   **Issue:** `app.py` uses a duplicate, hardcoded `asset_map` dictionary to validate image assets that diverges from `viewer.html` and the saved document state. It incorrectly adds `asset_014` and `asset_015`.
*   **Fix Needed:** `render_check` must resolve images by reading `doc.assets` dynamically from the saved JSON itself (`data.get("assets", [])`), ensuring the server and client asset registries remain synchronized.

### **BUG-C2: `app.py` `validate_schema()` is dangerously permissive**
*   **Location:** `app.py`, `validate_schema()`
*   **Issue:** The save validator accepts *any* JSON that has either `version+elements` OR `zoom+scroll+elements`. Malformed, empty, or half-migrated V1 documents can be saved, silently overwriting good backups.
*   **Fix Needed:** Tighten schema to explicitly require `version === 2` and ensure `elements` is a list. Reject `version: 1` documents during `POST` operations (V1 should only be accepted on `GET` for migration).

### **BUG-C3: `get_menu()` injects a `status` field into the saved document**
*   **Location:** `app.py`, `get_menu()`
*   **Issue:** The GET route forcibly injects `data["status"] = status_info` directly into the document object. If the editor modifies and POSTs this back without stripping the field, `status` becomes permanently saved in `menu_data.json` and compounds.
*   **Fix Needed:** Return `status` separated from document data (e.g., `{"data": {...doc...}, "status": {...}}`), or strip it client-side before any save.

### **BUG-C4: Upload endpoint returns incomplete asset data**
*   **Location:** `app.py`, `upload_image()` (`/api/upload-image`)
*   **Issue:** The endpoint returns `{"status":"ok","filename":"...","url":"/Images/..."}` but fails to return a complete `storage` object. The client is forced to guess the structure, risking a desync between the `assetId` mapping and `storage.originalUrl`.
*   **Fix Needed:** The server response should return the exact storage block the editor expects: `{"status": "ok", "storage": {"originalUrl": "/Images/..."}}`.

### **BUG-C5: Backup timestamp NameError risk**
*   **Location:** `app.py`, `save_menu()`
*   **Issue:** The `timestamp` variable is only assigned if `os.path.exists(DATA_FILE)`. If the file doesn't exist (first save), the script will throw a `NameError` when attempting to reference `timestamp` in the return ternary.
*   **Fix Needed:** Initialize `timestamp = None` before the conditional check to prevent `NameError`.

---

## 🟠 High Priority Bugs — Causes Wrong Behavior

### **BUG-H1: Viewer poll hashing misses settings changes**
*   **Location:** `viewer.html`, `pollMenu()`
*   **Issue:** The polling hash only covers the `elements` array. If document settings (like viewer settings or background) change, the hash remains identical, preventing a redraw.
*   **Fix Needed:** Update the hashing function to cover the entire document object `JSON.stringify(s)`, not just `s.elements`.

### **BUG-H2: `validate_schema()` lacks payload size limits**
*   **Location:** `app.py`, `save_menu()`
*   **Issue:** `request.data` is parsed and accepted regardless of size. A maliciously or accidentally bloated payload can fill the persistent volume.
*   **Fix Needed:** Reject incoming payloads exceeding a reasonable maximum size (e.g., `if len(request.data) > 5_000_000: return 413`).

### **BUG-H3: Unauthenticated Production Debug Endpoint**
*   **Location:** `app.py`, `/api/menu-debug`
*   **Issue:** The endpoint returns the complete raw `menu_data.json` with no authentication, leaving production data publicly exposed.
*   **Fix Needed:** Remove the endpoint entirely or gate it behind an environment-variable-backed secret query parameter (`?key=XXXX`).

### **BUG-H4: Unbounded backup growth**
*   **Location:** `app.py`, `save_menu()`
*   **Issue:** Every save creates a timestamped copy in `/app/data/backups/`. Over time, this unbounded growth will exhaust Railway's persistent volume storage space.
*   **Fix Needed:** Implement a pruning mechanism to retain only the N most recent backups (e.g., 20) and delete older ones after every save.

### **BUG-H5: `export-utils.js` blindly inserts PNG `pHYs` chunks**
*   **Location:** `export-utils.js`, `inject300DpiAndDownload()`
*   **Issue:** The script blindly inserts the `pHYs` chunk at byte 33 (`bytes.slice(0, 33)`). If the `canvas.toBlob()` PNG includes any non-standard chunk before `IHDR`, this will corrupt the output file.
*   **Fix Needed:** Verify the `IHDR` chunk signature at bytes 12–15 (`bytes[12]===73 && bytes[13]===72 && bytes[14]===68 && bytes[15]===82`) before assuming offset 33 is safe.

### **BUG-H6: `restore` endpoint lacks schema validation**
*   **Location:** `app.py`, `restore_menu()`
*   **Issue:** Backups are restored by blindly copying the backup over `DATA_FILE`. If a backup is corrupted or is an outdated V1 file, the live system is instantly broken.
*   **Fix Needed:** Call `validate_schema(backup_data)` on the contents of the backup file *before* executing the filesystem overwrite.

---

## 🟡 Medium Priority Bugs — Tech Debt & Future Risks

### **BUG-M1: Dual `/Images/` route caching conflict**
*   **Location:** `app.py`, static routes
*   **Issue:** There is a specific route for `/Images/<path:filename>` and a generic static proxy fallback `/<path:path>`. The generic fallback also explicitly checks `.png`/`.jpg` extensions and applies `Cache-Control`. If Flask routing prioritization changes, caching logic will clash.
*   **Fix Needed:** Remove image extension checks from the fallback `static_proxy`; leave image caching strictly to the `/Images/` route.

### **BUG-M2: `PROTECTED_ASSETS` includes non-existent `Asset5.png`**
*   **Location:** `app.py`, `PROTECTED_ASSETS` definition
*   **Issue:** Generated as `{f"Asset{i}.png" for i in range(1, 15)}`, which includes `Asset5.png`. However, documentation and real assets confirm `Asset5.png` does not exist, creating a reality mismatch.
*   **Fix Needed:** Use an explicit `set` of exact protected asset names rather than a generated range.

### **BUG-M3: Upload endpoint lacks file type validation**
*   **Location:** `app.py`, `upload_image()`
*   **Issue:** Any file (regardless of extension or MIME type) can be uploaded and written to `/Images/` via base64 decoding. There is no magic number check or strict sanitization.
*   **Fix Needed:** Enforce strict checks on base64 headers/magic numbers (`\x89PNG`, `\xFF\xD8`) and enforce allowed extensions.

### **BUG-M4: `app.py` contains meaningless build artifacts**
*   **Location:** `app.py` bottom
*   **Issue:** The last line `# Hardened Layers Panel & Asset Management v2.0` is leftover noise that implies `app.py` is an auto-generated file.
*   **Fix Needed:** Remove the comment to prevent agent confusion.

### **BUG-M5: `export-utils.js` repeatedly reconstructs CRC32 table**
*   **Location:** `export-utils.js`, `crc32()`
*   **Issue:** The 256-entry lookup table is rebuilt inside the function on every call instead of being cached at the module level.
*   **Fix Needed:** Lift the CRC32 table generation out of the function scope.