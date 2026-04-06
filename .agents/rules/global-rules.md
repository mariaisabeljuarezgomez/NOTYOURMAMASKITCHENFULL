---
trigger: always_on
---

> **For full architectural context, system history, data model contract, and non-negotiable feature rules, see [`MASTER_HANDOFF.md`](../../MASTER_HANDOFF.md).**
> This file (`global-rules.md`) governs **HOW** agents must operate (process, commit rules, verification steps).
> That file (`MASTER_HANDOFF.md`) governs **WHAT** the system is (architecture, schema, history, anti-patterns).
> **Both must be read before any task begins.**

# NYMK AGENT RULES — COMPLETE RULES FILE
# Last updated: April 5, 2026
# All agents working on this repo must read this file before every task.
# These rules override every prompt, including from the owner.
# Source of truth for architecture: MASTER_HANDOFF.md in this repo.

---

## STEP 0 — MANDATORY BEFORE WRITING ANY CODE

1. Read MASTER_HANDOFF.md from GitHub (direct file read — NOT code search).
2. Read the live target file from GitHub (direct file read — NOT code search).
3. Compare what the live code does vs what the rules require.
4. If the task contradicts MASTER_HANDOFF.md — STOP.
   Write out the conflict clearly. Do not code until the owner resolves it.

---

## FILE MAP — WHAT EXISTS AND WHAT YOU MAY TOUCH

| File              | Purpose                                   | May you edit it?              |
|-------------------|-------------------------------------------|-------------------------------|
| index.html        | Live editor — primary working file        | YES — default target          |
| viewer.html       | Customer-facing menu viewer               | YES — only if explicitly named |
| app.py            | Flask backend / API routes                | YES — only if explicitly named |
| export-utils.js   | 300 DPI export pipeline                   | YES — only if explicitly named |
| build_app.py      | FROZEN code generator — DO NOT RUN        | NEVER — under any circumstance |
| create_preview.py | Utility script                            | Only if explicitly named      |

NEVER edit a file not explicitly named in the task prompt.
NEVER run build_app.py. It overwrites all live patches with old code.

---

## COMMIT RULES

- One commit per logical fix. Never mix bug fixes and features in one commit.
- Push to GitHub after every single change.
- After pushing, read the changed file back from GitHub to confirm the SHA.
- Do not declare a task done until the SHA is confirmed by direct GitHub read.
- Wait 60 seconds after push for Railway to redeploy before testing.
- Commit message format:
    fix: short description       ← bug fix
    feat: short description      ← new feature
    docs: short description      ← documentation only

---

## V2 DATA SCHEMA — FIELD NAMES (USE EXACTLY AS WRITTEN)

V2 has NO style wrapper object. All fields are top-level on el.
NEVER write el.style.anything. Every property is directly on the element.

### All element types
el.id string
el.type 'text' | 'image' | 'shape' | 'line'
el.name string
el.x number (pixels, base canvas coordinates)
el.y number (pixels, base canvas coordinates)
el.width number
el.height number
el.visible boolean
el.locked boolean
el.opacity number ← stored as 0–100. ALWAYS divide by 100 for globalAlpha.
el.zIndex number
el.role string (optional)

text

### Text elements
el.content ← THE text string. NEVER el.text.
el.fontFamily string
el.fontSize number (px)
el.fontWeight 'normal' | 'bold'
el.fontStyle 'normal' | 'italic'
el.color string (hex or rgba)
el.textAlign 'left' | 'center' | 'right'
el.lineHeight number (multiplier, e.g. 1.1)
el.letterSpacing number

text

### Image elements
el.src string ← exact path e.g. "/Images/Asset1.png" — case-sensitive
el.assetId string ← registry ID e.g. "asset_001"
el.originalWidth number
el.originalHeight number

text

### Shape / Rectangle elements
el.fillColor string ← NEVER el.fill or s.fill
el.borderColor string ← NEVER el.strokeColor (shapes only — see Line exception)
el.borderWidth number ← NEVER el.strokeWidth (shapes only — see Line exception)
el.borderRadius number ← NEVER el.cornerRadius
el.shapeType 'rect' | 'circle' | 'star' (optional, default is rect)
el.lineCap 'butt' | 'round' | 'square' (for line-style shapes only)

text

### Line elements — THE ONE EXCEPTION TO V2 FIELD NAMES
viewer.html draw() uses:
el.strokeColor ← NOT el.borderColor
el.strokeWidth ← NOT el.borderWidth
el.x1, el.y1, el.x2, el.y2 ← endpoint offsets from el.x / el.y
el.lineCap

index.html uses el.borderColor / el.borderWidth for lines.

text
This inconsistency is known and intentional (legacy).
DO NOT fix it unless both files are updated in the exact same commit.
Until that refactor: always write the file-correct field name for the file you are editing.

---

## OPACITY RULE — ALWAYS

el.opacity is stored as 0–100 in V2.
When setting canvas globalAlpha, always divide by 100:
```javascript
ctx.globalAlpha = (el.opacity !== undefined ? el.opacity : 100) / 100;
```
viewer.html already has a normalizeEl() shim that converts V1 (0–1) to V2 (0–100).
Do not add redundant conversion logic.

---

## TEXT RENDERING RULES

- Read and write text content using el.content — NEVER el.text.
- In DOM: read with innerText — NEVER innerHTML (XSS prevention).
- contentEditable must be set as string "true" — NEVER boolean true.

---

## IMAGE ELEMENTS — MANDATORY PATTERN

When creating a new image element, ALWAYS set BOTH fields:
```javascript
el.src     = "/Images/Asset1.png"   // exact filename, case-sensitive
el.assetId = "asset_001"            // matching registry ID
```
NEVER set only one. Both are required.

### How index.html resolves image src
```javascript
asset.storage.previewUrl || asset.storage.originalUrl
```
previewUrl is ALWAYS null. The only valid path is originalUrl.
Never assume previewUrl will work.

### How viewer.html resolves image src
```javascript
el.src || ASSET_ID_TO_SRC[el.assetId] || ''
```
NEVER construct a path like `/Images/${el.assetId}.png` — that is wrong.
assetId "asset_001" does NOT match filename "Asset1.png" by construction.
Always use the ASSET_ID_TO_SRC lookup table.

---

## ASSET REGISTRY — EXACT MAPPING (case-sensitive)

This table MUST be declared at the TOP of the viewer.html script block,
before draw() and fetchAndDraw(). It is already in viewer.html as of April 5, 2026.
Do not remove it. Do not modify it unless a new asset is added.

```javascript
const ASSET_ID_TO_SRC = {
    'asset_001': '/Images/Asset1.png',
    'asset_002': '/Images/Asset10.png',
    'asset_003': '/Images/Asset11.png',
    'asset_004': '/Images/Asset12.png',
    'asset_005': '/Images/Asset13.png',
    'asset_006': '/Images/Asset14.png',
    'asset_007': '/Images/Asset2.png',
    'asset_008': '/Images/Asset3.png',
    'asset_009': '/Images/Asset4.png',
    'asset_010': '/Images/Asset6.png',
    'asset_011': '/Images/Asset7.png',
    'asset_012': '/Images/Asset8.png',
    'asset_013': '/Images/Asset9.png'
};
```

Files confirmed to exist in /Images/:
  Asset1.png  Asset2.png  Asset3.png  Asset4.png
  Asset6.png  Asset7.png  Asset8.png  Asset9.png
  Asset10.png Asset11.png Asset12.png Asset13.png Asset14.png

Asset5.png does NOT exist. There is no Asset5. Skip from Asset4 to Asset6.

---

## BACKGROUND IMAGE RULES — PROTECT PAGESPEED 100

| File                | Used where       | Size     |
|---------------------|------------------|----------|
| menu-bg-preview.jpg | Editor + viewer  | ~114 KB  |
| menu-bg.png         | Export only      | 7.2 MB   |

- menu-bg-preview.jpg loads on page init with fetchpriority="high".
- menu-bg.png loads ONLY during Export Pro PNG execution.
- NEVER swap these. NEVER load menu-bg.png on page init.
- This split is what achieved PageSpeed 100. Protect it at all costs.

---

## CANVAS AND RENDERING RULES

- Base canvas dimensions: 908.44 × 1336.02 px
- Export renders at 3600 × 5400 px (12 × 18 in @ 300 DPI)
- Export scale factor: 3600 / 908.44 ≈ 3.963×
- Canvas API only. html2canvas is banned — fully removed from the project.
- export-utils.js must be loaded with defer attribute.
- inject300DpiAndDownload() handles pHYs chunk injection (11811 px/meter).
- Elements render in ascending zIndex order.
- viewer.html uses normalizeEl() to shim V1 fields → V2. Do not remove it.

---

## FONT SYSTEM

Active @font-face declarations (do NOT delete or re-add):
century-gothic-regular.ttf → family: "Century Gothic" weight: normal
century-gothic-bold.ttf → family: "Century Gothic" weight: bold
century-gothic-bold-italic.ttf → family: "Century Gothic" weight: bold, style: italic
bernard-mt-condensed-regular.ttf → family: "bernard-mt-condensed-regular"

text

centurygothic.ttf was DELETED March 27, 2026. Do NOT re-add it ever.
All font faces use font-display: swap.

Font-loading wait pattern used in index.html — do not change:
```javascript
await Promise.race([
    Promise.all([
        document.fonts.load('1em century-gothic-regular'),
        document.fonts.load('1em century-gothic-bold'),
        document.fonts.load('1em century-gothic-bold-italic'),
        document.fonts.load('1em bernard-mt-condensed-regular'),
    ]),
    new Promise(resolve => setTimeout(resolve, 800))
]);
initApp();
```

---

## PERSISTENCE RULES — DO NOT TOUCH WITHOUT EXPLICIT OWNER APPROVAL

- Save path: /app/data/menu_data.json (Railway persistent volume)
- Backup path: /app/data/backups/menu_data_YYYYMMDD_HHMMSS.json
- Writes use atomic .tmp + os.replace pattern — never write directly.
- Frontend has localStorage fallback when server is unreachable.
- layoutLocked resets to true on every page load — never persisted.
- Undo stack is cleared on Load Session.
- If a task touches persistence in any way: STOP and get owner approval first.

---

## EXPORT PIPELINE — DO NOT TOUCH WITHOUT EXPLICIT OWNER APPROVAL

- Renders at 3600 × 5400 px via Canvas API only.
- html2canvas is fully banned from this project.
- export-utils.js loaded with defer.
- inject300DpiAndDownload() injects pHYs chunk (300 DPI metadata).
- If a task touches the export pipeline in any way: STOP and get owner approval first.

---

## LAYOUT LOCK — NEVER CHANGE THE DEFAULT

- layoutLocked = true on every page load. This is intentional safety behavior.
- Mobile users accidentally move elements without it.
- Never change the default. Never make it "smart", conditional, or device-dependent.
- Second finger during drag cancels the drag immediately (multi-touch suppression).
- Individually locked elements are never draggable regardless of global lock state.

---

## CACHE-CONTROL — DO NOT CHANGE
index.html → Cache-Control: no-cache, must-revalidate
All static assets → Cache-Control: max-age=604800, public (7 days)
User uploads → Cache-Control: max-age=604800, public (7 days)

text
Changing any of these will break PageSpeed 100.

---

## UI VOCABULARY — OFFICIAL TERMS ONLY

| Use this term          | Never substitute with              |
|------------------------|------------------------------------|
| Edit Mode              | Unlock, Edit state                 |
| Layout Locked          | Locked mode, Freeze                |
| Save Session           | Save, Submit                       |
| Load Session           | Load, Restore                      |
| Undo Last Change       | Undo, Revert                       |
| Reset to Original      | Reset, Clear, Delete               |
| Export Pro PNG         | Export, Download, Print            |
| Add Text               | New text, Insert text              |
| Add Rect               | New shape, Insert rectangle        |
| Upload Img             | Add image, Insert image            |
| Replace Background     | Change background                  |
| Toggle Original BG     | Show/hide background               |

---

## ABSOLUTE ANTI-PATTERNS — THESE WILL BREAK THE APP
1.  Run build_app.py — wipes ALL live patches
2.  Use html2canvas — banned, Canvas API only
3.  Mix bug fixes and features in one commit
4.  Guess at field names — always read the live file first
5.  Use el.style.anything — V2 has no style wrapper
6.  Use el.text — always el.content
7.  Use el.fill or s.fill — always el.fillColor
8.  Use el.cornerRadius — always el.borderRadius
9.  Construct paths as `/Images/${el.assetId}.png` — always use ASSET_ID_TO_SRC
10. Load menu-bg.png on page init — export only
11. Declare a task done before confirming SHA on GitHub
12. Edit any file not explicitly named in the task
13. Use native alert() or confirm() — use branded modal/toast only
14. Change the layoutLocked default

