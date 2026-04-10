# NOTYOURMAMASKITCHENFULL — Complete Agent Handover Document

**Repository:** https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL  
**Live App:** https://web-production-3e17d.up.railway.app/  
**Platform:** Railway (auto-deploys from main branch)  
**Stack:** Flask (app.py) + PostgreSQL (Railway DB) + Cloudinary (image hosting) + single-file frontend (index.html + export-utils.js)  
**Last Known Good SHA:** Unknown — the system has not been fully stable since the ephemeral→database migration  
**Current Broken SHA:** 8a2dba5db1999e83306c2144e9c249b2c04f5c18  

---

## 1. What This App Is

A professional restaurant menu editor. The owner (Rogelio) uses it to:
- Design a full-page menu (908×1336px canvas) with text, images, and shapes
- Upload a background image (stored in Cloudinary, referenced by URL in the DB)
- Add assets (logos, decorative images) from a left-side asset tray
- Export a print-ready PNG
- Save/load the canvas state to/from PostgreSQL

A separate viewer app (viewer.html) reads the same database and displays the menu publicly.

---

## 2. The Architecture Migration That Broke Everything

### Before (Working System)
- **Storage:** Railway mounted volume (persistent disk) at `/data/`
- **Background image:** Stored as a file on disk (`/data/background.jpg`), served directly
- **Canvas JSON:** Stored as a file on disk (`/data/menu_data.json`)
- **Assets:** Stored as files on disk, listed from the folder
- **Font files (.ttf):** Stored in the repo root, served as static files by Flask

### After (Current Broken System)
- **Storage:** PostgreSQL database only — NO mounted volume
- **Background image:** Uploaded to Cloudinary, URL stored in the `canvas_json` table
- **Canvas JSON:** Stored as JSONB in PostgreSQL, table: `canvas_json`, record id: `'main'`
- **Assets:** Uploaded to Cloudinary, URLs stored in a `assets` table in PostgreSQL
- **Font files (.ttf):** NOT in the repo, NOT served — causing 404 errors

### Why This Migration Was Done
Railway's ephemeral filesystem means anything written to disk is lost on every deploy or restart. The mounted volume was removed or stopped working, causing all saved data to disappear. The decision was made to move all persistence to PostgreSQL and all images to Cloudinary, which are both persistent.

### What the Migration Broke
The migration introduced a cascade of new bugs because the frontend (index.html) was originally written assuming a simple file-based backend. The transition was never cleanly completed — multiple agents made partial fixes that conflicted with each other over dozens of commits.

---

## 3. Current Active Bugs (All Unresolved)

### BUG A: Every Element Is Duplicated (x2) On Page Load

**Symptom:** When the page loads, every element on the canvas appears twice — two backgrounds, two of every text, two of every shape. The Cloudinary background URL appears twice in the Network panel on load.

**Root Cause (most likely):** `_mergeLoadedDoc()` is being called twice during initialization. The `window.onload` function has a waterfall that fetches from `/api/menu`, but there is also a fallback path. Multiple agents attempted to fix this by adding flags (`initialRenderDone`, `_mergeLoadedDoc` guards) but the fix was never actually landing correctly because agents were truncating the file when writing it back via MCP tools (the GitHub API truncates large files). The flag is either not in the right scope, or `_mergeLoadedDoc` is still being called from two separate code paths.

**What was tried:**
- Added `initialRenderDone` flag (did not fix — likely placed in wrong scope or overwritten)
- Added `doInitialRender()` wrapper function
- Removed `fitCanvasToScreen()` from `_mergeLoadedDoc` (correct, but not sufficient alone)
- Multiple "waterfall" rewrites of `window.onload`

**What was NEVER correctly verified:** Whether the actual deployed file on Railway contains the fix, because agents kept truncating the file during MCP pushes.

---

### BUG B: Text Elements Are Unclickable, Uneditable, and Unmovable

**Symptom:** After adding a text element, it cannot be clicked to select it, cannot be double-clicked to edit, and cannot be dragged. The selection bar never appears for text.

**Root Cause (most likely — two compounding issues):**

1. **The `render()` function destroys and recreates all DOM elements every time it runs.** The `attach(el)` function that wires up mouse/click handlers is called during render. If `render()` is called at ANY point after the user interacts with a text element (e.g., because an asset loaded, because a background flickered), the DOM element is destroyed and recreated WITHOUT the user's interaction being preserved. The new DOM element is technically correctly attached, but any in-progress drag or edit state is lost.

2. **The `pointer-events` CSS chain.** The CSS rule `.editable-element.selected *:not(.resize-handle):not(.editable-text) { pointer-events: none; }` was intended to block clicks on child elements passing through to the wrong handler. However, if `.editable-text` somehow does not have `pointer-events: auto !important;` in the current deployed CSS, text clicks are silently swallowed.

3. **stale `document.onmousemove` handlers.** If a drag operation was interrupted (e.g., by a render() wiping the element mid-drag), `document.onmousemove` and `document.onmouseup` remain set from the previous drag. The next mousedown on a text element immediately triggers the OLD drag handler instead of the new one, making the element appear frozen.

**What was tried:**
- Added `document.onmousemove = null; document.onmouseup = null;` at start of `attach(el)` mousedown
- Added CSS `pointer-events: auto !important` to `.editable-text`
- V1→V2 migration shim for old data fields
- `el.onclick` → `selectById()` explicit call
- `dataset.id` fix in `onCanvasClick`
- `attach(el)` before `appendChild` in render

**None of these fixed it** because the underlying cause (render() being called redundantly and wiping live DOM elements) was never eliminated.

---

### BUG C: Background Flashes On/Off Every Time Any Element Is Added

**Symptom:** Every time you add a shape, text, or click an asset, the background image disappears for ~1 second then reappears. In the Network panel, the Cloudinary background URL is fetched again each time.

**Root Cause:** `render()` clears `innerHTML` of `#elements-layer` and rebuilds ALL elements from the `elements[]` array on every call. The background is stored as an element in that array with `type: 'image'` and `role: 'background'`. When render() runs, it creates a new `<img>` tag pointing to the Cloudinary URL. The browser has to re-fetch or re-decode that image every time, causing the flash. The background is not cached in the DOM — it is destroyed and recreated on every single render call.

**What was tried:**
- Deduplication logic on load
- z-index enforcement (zIndex: 0 for background, -1 in CSS)
- `setSelectedAsBackground()` clearing old background role
- Base64 guard to prevent base64 data from being stored
- Consolidating background management to single DB source

**What was NEVER done:** Separating the background element from the `render()` loop entirely. The background should be rendered into a dedicated DOM layer that is NEVER cleared by render(), and only updated when the user explicitly changes the background.

---

### BUG D: Font Files 404

**Symptom:** Console errors:
```
century-gothic-bold.ttf 404
century-gothic-bold-italic.ttf 404
century-gothic-regular.ttf 404
```

**Root Cause:** The `.ttf` files (`century-gothic-bold.ttf`, `century-gothic-bold-italic.ttf`, `century-gothic-regular.ttf`, `bernard-mt-condensed-regular.ttf`) are referenced in `@font-face` CSS rules in `index.html` but are NOT present in the repository and NOT served by Flask. They were likely stored on the old mounted volume and lost during the migration.

**What was tried:** Nothing successful. One commit claimed to "fix font hosting" but the files were never actually added to the repo.

**Fix required:** Either add the actual .ttf files to the repo root AND add a Flask static route for them, OR replace the `@font-face` declarations with Google Fonts equivalents for Century Gothic alternatives (e.g., `Century Gothic` → `Nunito` or serve via CDN).

---

## 4. What Each Agent Did and Why It Failed

### Manus Agent (commits 638723b, 3fb4c6b)
- Did a large 12-bug fix pass, introduced uuid asset_id, session cap, DB sync on restore
- **Broke:** Rewrote large sections of index.html, which later agents could not read completely due to MCP tool truncation

### Google Jules (commit 4cb7fe4)
- Fixed `el.dataset.id || el.id` fallback and `select(id)` → `selectById(id)`
- **Correct fix** for one sub-symptom of Bug B, but Bug B has multiple root causes so it alone wasn't sufficient

### letsgetcreative agent (multiple commits April 9-10)
- Fixed zIndex for text elements above background
- Moved `attach(el)` before `appendChild`
- Added `fitCanvasToScreen` setTimeout wrap
- Attempted waterfall `window.onload` rewrites
- **Problem:** Every time this agent wrote index.html back via MCP, the file was TRUNCATED. The GitHub MCP tool has a file size limit and silently cuts off large files. The agent kept writing partial files thinking they were complete. This is the single biggest source of ongoing breakage.

### Perplexity (this agent — today)
- Correctly diagnosed all 4 root causes in analysis
- Approved the other agent's fix plan (correct plan)
- **Problem:** Cannot apply fixes safely because MCP `create_or_update_file` truncates index.html (the file is too large for the tool). Every attempt by any agent using this tool has corrupted the file. This was stated by the user repeatedly and ignored.

---

## 5. The Core Technical Reason Nothing Gets Fixed

**index.html is too large for the GitHub MCP API tool.** The file exceeds the safe size for the `create_or_update_file` MCP call. When any agent writes it back, the file is silently truncated — the last portion of the JavaScript is cut off. The page then fails with syntax errors or missing functions. Every "fix" that was applied this way actually made things worse because it introduced partial code.

**The only safe ways to modify index.html are:**
1. Clone the repo locally with `git clone`, edit the file directly, then `git push`
2. Use the GitHub web editor (edit in browser, no size limit)
3. Use `push_files` MCP tool with the COMPLETE file content (not partial)
4. Use an agent that operates in a real shell environment (Manus, local Cursor/VS Code agent)

---

## 6. Correct Fix Strategy for the Next Agent

### Step 1 — Fix the Font 404s First (Easiest)
Either:
- Add the 4 .ttf files to the repo root and add `app.send_from_directory` route in app.py
- OR replace `@font-face` rules with Google Fonts CDN links for equivalent fonts

### Step 2 — Fix Bug C (Background Flash) with a Structural Change
Move the background out of the `render()` loop:
```javascript
// In render(), skip elements where el.role === 'background'
// Instead, maintain a separate function: renderBackground()
// renderBackground() writes only to a dedicated #background-layer div
// Only call renderBackground() when the background actually changes
// This div is NEVER cleared by render()
```

### Step 3 — Fix Bug A (Duplication) 
The `window.onload` must call `_mergeLoadedDoc` EXACTLY ONCE. Use this pattern:
```javascript
window.onload = async function() {
  let data = null;
  try {
    const r = await fetch('/api/menu');
    if (r.ok) { const s = await r.json(); if (s && s.elements) data = s; }
  } catch(e) {}
  if (!data) data = DEFAULT_MENU_DATA;
  _mergeLoadedDoc(data);  // ONE call, no fallback second call
  // fitCanvasToScreen AFTER merge, not inside merge
  setTimeout(fitCanvasToScreen, 100);
};
```
Remove ALL other calls to `_mergeLoadedDoc` and `render()` from `window.onload`.

### Step 4 — Fix Bug B (Text Interaction)
After fixing Bug C (so render() doesn't run redundantly), most of Bug B should resolve. Additionally:
- At the very start of `attach(el)` mousedown handler: `document.onmousemove = null; document.onmouseup = null;`
- Ensure the `render()` function is NEVER called except: (a) initial load, (b) after a deliberate add/delete/undo operation, (c) after save/load. It must NOT be called on every click, hover, or property change.

---

## 7. Database Schema Reference

```sql
-- Canvas JSON storage
CREATE TABLE canvas_json (
  id TEXT PRIMARY KEY,   -- always 'main'
  data JSONB,            -- full canvas state as JSON
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Asset storage  
CREATE TABLE assets (
  id SERIAL PRIMARY KEY,
  asset_id TEXT UNIQUE,
  url TEXT,              -- Cloudinary URL
  public_id TEXT,        -- Cloudinary public_id for deletion
  name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Global settings (viewer video URLs etc.)
CREATE TABLE global_settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
```

### Canvas JSON Structure (data field)
```json
{
  "background": "https://res.cloudinary.com/...",  
  "elements": [
    {
      "id": "txt_1234567890",
      "type": "text",
      "x": 100, "y": 200, "w": 300, "h": 50,
      "text": "MENU ITEM",
      "fontSize": 24,
      "fontFamily": "century-gothic-bold",
      "color": "#ffffff",
      "bold": false, "italic": false, "underline": false,
      "align": "center",
      "lineHeight": 1.2,
      "opacity": 1,
      "zIndex": 10,
      "locked": false,
      "role": null
    },
    {
      "id": "img_1234567891",
      "type": "image",
      "role": "background",
      "src": "https://res.cloudinary.com/...",
      "x": 0, "y": 0, "w": 908, "h": 1336,
      "zIndex": 0,
      "locked": true,
      "opacity": 1
    }
  ]
}
```

---

## 8. Flask API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serves index.html |
| `/api/menu` | GET | Returns canvas JSON from DB |
| `/api/menu` | POST | Saves canvas JSON to DB |
| `/api/assets` | GET | Returns list of all assets |
| `/api/upload-asset` | POST | Uploads image to Cloudinary, saves URL to assets table |
| `/api/upload-background` | POST | Uploads background to Cloudinary, updates canvas_json |
| `/api/delete-asset/<asset_id>` | DELETE | Deletes from Cloudinary and assets table |
| `/api/global-settings` | GET/POST | Viewer video URL settings |
| `/viewer` | GET | Serves viewer.html (public display) |
| `/export-utils.js` | GET | Serves the PNG export utility JS |

---

## 9. Environment Variables Required on Railway

```
DATABASE_URL          = postgresql://... (Railway provides automatically)
CLOUDINARY_CLOUD_NAME = (from Cloudinary dashboard)
CLOUDINARY_API_KEY    = (from Cloudinary dashboard)  
CLOUDINARY_API_SECRET = (from Cloudinary dashboard)
```

---

## 10. Critical Rules for the Next Agent

1. **DO NOT use `create_or_update_file` MCP tool on index.html.** It truncates the file. Use `push_files` with complete content, or work in a local shell.
2. **DO NOT call render() to fix visual glitches.** render() is the cause of most visual glitches, not the cure.
3. **DO NOT add more flags, guards, or wrappers on top of existing broken code.** The code needs structural changes, not patches on patches.
4. **VERIFY the deployed file on Railway** after every push with a hard refresh (Ctrl+Shift+R) before declaring anything fixed.
5. **Check the Network panel** after every fix — if the Cloudinary background URL appears more than once, the duplication bug is still active.
6. **Read the FULL index.html before making any changes.** It is approximately 6,000+ lines. Do not assume you know where a function is — search for it.

---

## 11. Commit History Summary (Most Recent First)

| SHA | Date | Agent | What It Did | Did It Work? |
|-----|------|-------|-------------|--------------|
| 8a2dba5 | Apr 10 | letsgetcreative | Rendering/text/init fixes | NO |
| f11d8d1 | Apr 10 | letsgetcreative | fitCanvasToScreen setTimeout | NO |
| 5ee3d5e | Apr 10 | letsgetcreative | Init, dedup, font hosting | NO |
| 10ca33f | Apr 10 | letsgetcreative | Waterfall init | NO |
| 7dc7c62 | Apr 10 | letsgetcreative | DB query alignment | NO |
| 01109157 | Apr 10 | letsgetcreative | SSL + export routing | PARTIAL |
| 017ddc4 | Apr 10 | letsgetcreative | Full DB migration | INTRODUCED BUGS |
| 6f32d7d | Apr 10 | letsgetcreative | DB-only save | PARTIAL |
| 8b643d8 | Apr 10 | letsgetcreative | BG integrity, dedup, base64 guard | NO |
| ca7a67a | Apr 10 | letsgetcreative | BG dedup on load, localStorage purge | NO |
| f676b66 | Apr 10 | letsgetcreative | BG z-index enforcement | NO |
| ccd7992 | Apr 10 | letsgetcreative | Session persistence | NO |
| 5749ce3 | Apr 10 | mariaisabeljuarezgomez | Global paste listener | YES (feature) |
| 192778400 | Apr 10 | mariaisabeljuarezgomez | Fixes A, B, C surgical | NO |
| d88d79f | Apr 10 | mariaisabeljuarezgomez | Color hex, render optimization | NO |
| b88929c | Apr 10 | mariaisabeljuarezgomez | Remove render guard, clear BG role | NO |
| fe10a47 | Apr 10 | mariaisabeljuarezgomez | json.loads() fix in app.py | YES (backend) |
| c9e601 | Apr 10 | letsgetcreative | Consolidate BG to single DB source | NO |
| d8cb221 | Apr 10 | letsgetcreative | addText zIndex fix | YES (partial) |
| f35173f | Apr 10 | mariaisabeljuarezgomez | Remove hardcoded menu-bg img | YES |
| 98c6ca9 | Apr 9 | mariaisabeljuarezgomez | Premium UI, rulers, guides | YES (features) |
| 638723b | Apr 9 | Manus | 12-bug fix pass | PARTIAL |

