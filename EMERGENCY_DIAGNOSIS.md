# 🚨 EMERGENCY DIAGNOSIS — Text Element Selection Failure
**Status:** UNRESOLVED as of April 9, 2026 11:40 AM MDT  
**Repo:** https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL  
**Live App:** https://web-production-3e17d.up.railway.app/  
**Read first:** `MASTER_HANDOFF.md` (canonical architecture), `.agents/rules/global-rules.md` (agent rules)  
**File to fix:** `index.html` — the ONLY live source file. Do NOT touch any other file.

---

## ⚠️ THE PROBLEM IN ONE SENTENCE

Clicking a text element on the canvas does NOT select it. The element either does not respond to clicks, or appears to select and immediately deselects.

---

## 🕵️ HISTORY OF THIS BUG — READ THIS FIRST

### Fix Attempt #1 — Commit `1ef7db8` (April 9, 2026 morning)
**What Manus did:**  
Added `el.dataset.id = d.id;` to all three element creation blocks in `render()` — Images, Lines, and Text/Shapes.  
**Claimed fix:** "Text elements were immediately deselecting because `dataset.id` was missing on their DOM nodes. `onCanvasClick` couldn't identify the element and defaulted to `deselect()`."

**Result:** STILL BROKEN. The fix was either incomplete or there is an additional cause.

### Previous Bug — Commit `05e1bd6` (Lasso Ghost-Clear, April 2026)
The lasso selection had the exact same symptom — selections disappearing immediately — caused by a `click` event firing after `mouseup` and calling `deselect()`. Fixed with `if (_lassoJustFired) return;` in `onCanvasClick`. See `MASTER_HANDOFF.md` → `Bug Autopsy` section for full details.

---

## 🔬 LIVE CODE FINDINGS — WHAT'S IN index.html RIGHT NOW

### Finding 1 — `dataset.id` IS Present on All Element Types

After commit `1ef7db8`, `render()` in the live code DOES set `el.dataset.id = d.id` on all three blocks:

```javascript
// IMAGE block:
el = document.createElement('div');
el.id = d.id;
el.dataset.id = d.id;   // ✅ PRESENT

// LINE block:
el = document.createElement('div');
el.id = d.id;
el.dataset.id = d.id;   // ✅ PRESENT

// TEXT/SHAPE else block:
el = document.createElement('div');
el.id = d.id;
el.dataset.id = d.id;   // ✅ PRESENT
```

This means commit `1ef7db8` WAS applied correctly. The `dataset.id` fix is in the live code.  
**But the bug persists.** Therefore `dataset.id` was NOT the root cause, or is NOT the only cause.

---

### Finding 2 — CRITICAL: Text Elements Use `d.text` NOT `d.content`

In the `render()` function, line for text rendering:
```javascript
if(d.type==='text') { 
    el.innerText = d.text;   // ⚠️ Uses d.text, NOT d.content
```

The V2 schema mandates `el.content`, NEVER `el.text`. But `docV2.elements[]` in the live embedded JSON shows text stored under the `"text"` field:
```json
{"id": "txt_0", "type": "text", "text": "SANDWICHES", ...}
```

So the embedded data uses `text`, but the V2 contract says `content`. This is a **data model inconsistency** — the embedded elements never migrated to V2 properly. This may cause issues but is separate from the click bug.

---

### Finding 3 — CRITICAL: Background/Pointer Events Logic Blocks ALL Background-Role Elements

At the bottom of the `render()` forEach loop:
```javascript
if (d.isSystemBackground === true || d.layerRole === 'background') 
    el.style.pointerEvents = 'none';
```

⚠️ **This fires on ANY element with `layerRole === 'background'`**, not just system backgrounds.  
This DOES violate the Two-Background-Type Rule in `MASTER_HANDOFF.md` Section 6B Rule B.  
However, looking at the data, all text elements have `"layerRole": "content"` — so this is NOT causing the text selection failure directly.

---

### Finding 4 — `onCanvasClick` and `onViewportClick` Logic

The code defines:
```javascript
<main id="editor-viewport" onclick="onViewportClick(event)">
  <div id="menu-container" onclick="onCanvasClick(event)" ...>
```

The `_lassoJustFired` guard is already implemented from the previous fix. The question is: **what does `onCanvasClick` do when it receives a click on a text element?**

The click handler flow should be:
1. User clicks on text element DOM node
2. `e.target` = the text element div
3. `e.target.dataset.id` = the element's id (now present after fix `1ef7db8`)
4. Handler finds the element in `docV2.elements[]` and calls `select(id)`

**BUT:** The text element also has `el.contentEditable = false` set, and an `ondblclick` handler. If there is any interaction between the click handler and `contentEditable`, or if the event is being swallowed somewhere, selection could fail.

---

### Finding 5 — `layoutLocked` State

In the live `docV2`:
```javascript
settings: {
    layoutLocked: false,   // unlocked by default in embedded data
```

But in `initApp()` / page load logic, `layoutLocked` is set from:
```javascript
let layoutLocked = false
```

And the button in the header shows `🔓 Layout Unlocked` by default.

**However:** The `MASTER_HANDOFF.md` says `layoutLocked` resets to `true` on every page load. If the lock state is actually `true` but the UI shows `false`, clicks on elements would be silently blocked.

Check: Does `onCanvasClick` or `onCanvasMousedown` have `if (layoutLocked) return;` guards that prevent selection when locked?

---

### Finding 6 — `attach()` Function Not Visible in Retrieved Code

At the end of the render forEach:
```javascript
elementsLayer.appendChild(el); attach(el);
```

**`attach(el)` is the function that wires up pointer/mouse events to each element.** The full body of `attach()` was NOT returned in the code retrieval (index.html is very long — the retrieval was truncated). 

**This is the #1 suspect.** If `attach()` is calling `e.stopPropagation()` or overriding the click handler in a way that prevents the event from bubbling to `onCanvasClick`, selection would silently fail.

---

## 🎯 MOST LIKELY ROOT CAUSES (in priority order)

### Suspect #1 — `attach()` function (HIGHEST PROBABILITY)
`attach(el)` wires pointer events to each element. It almost certainly has:
- `el.onpointerdown` or `el.onclick` handlers
- These handlers select the element directly (bypassing `onCanvasClick`)
- If `attach()` calls `e.stopPropagation()`, the event never reaches `onCanvasClick`
- If `attach()` handles selection but calls the wrong identifier (e.g., `el.id` vs `el.dataset.id`), selection works for some element types but not others
- **The fix in `1ef7db8` set `dataset.id` but if `attach()` uses `el.id` directly (not `dataset.id`), nothing changed**

**What to look for in `attach()`:**
```javascript
function attach(el) {
    el.onpointerdown = (e) => {
        // Does this read e.target.dataset.id? or el.id? or something else?
        // Does it call e.stopPropagation()?
        // Does it call select() directly?
        // Does it check layoutLocked?
    }
}
```

### Suspect #2 — `layoutLocked` True at Runtime Even If UI Shows Unlocked
If `layoutLocked = true` and `onCanvasMousedown` has `if (layoutLocked) return;`, no element can be selected no matter what.

Test: Open browser console, type `layoutLocked` and press Enter. What does it return?

### Suspect #3 — `onCanvasClick` Deselect Path Still Triggering
Even with `dataset.id` present, if `onCanvasClick` traverses `e.target` upward (e.g., `closest('.editable-element')`) and the logic fails for some reason, it falls to `deselect()`.

Test: Add `console.log(e.target, e.target.dataset.id)` as the first line of `onCanvasClick`. Click a text element. What logs?

### Suspect #4 — `isEditingText = true` Stuck True
If `isEditingText` is `true` (stuck from a previous edit), `onCanvasClick` or `onCanvasMousedown` may skip selection logic.

Test: Open browser console, type `isEditingText` and press Enter.

### Suspect #5 — CSS `pointer-events: none` on Text Elements
In `render()`, the final rendering line:
```javascript
if (d.isSystemBackground === true || d.layerRole === 'background') 
    el.style.pointerEvents = 'none';
```
All text elements have `layerRole: 'content'` so this SHOULD not apply. But verify no other CSS rule is setting `pointer-events: none` on `.editable-text`.

Look at the CSS: `.editable-element.selected * { pointer-events: none; }` — This sets pointer-events to none on CHILDREN of selected elements, not the element itself. This should be fine.

---

## 🔧 HOW TO FIX THIS — STEP BY STEP

### Step 1 — Read the FULL index.html from GitHub
Do a direct GitHub file read. Do NOT use code search. The file is large. Get all of it.

### Step 2 — Find and read `attach()` completely
Search for `function attach(` in the file. Read the entire function. This is the primary suspect.

### Step 3 — Find and read `onCanvasClick()` completely
Search for `function onCanvasClick(` or `onCanvasClick` assignment. Read it entirely.

### Step 4 — Find and read `onCanvasMousedown()` completely
Search for `function onCanvasMousedown(` or `onCanvasMousedown` assignment.

### Step 5 — Run these console tests on the live app
```javascript
// Test 1: Check lock state
layoutLocked

// Test 2: Check editing state  
isEditingText

// Test 3: Check if elements have dataset.id
document.querySelectorAll('.editable-element').forEach(el => console.log(el.id, el.dataset.id))

// Test 4: Intercept onCanvasClick
const orig = window.onCanvasClick;
window.onCanvasClick = function(e) { console.log('CANVAS CLICK', e.target, e.target?.dataset?.id); orig && orig.call(this, e); }
```

### Step 6 — Apply the surgical fix
Once root cause identified, make the SMALLEST possible change. One commit. One push. Verify SHA.

---

## 📋 COMPLETE ARCHITECTURE CONTEXT

### Data Model — How Text Elements Are Stored
Live `docV2.elements[]` stores text elements like this:
```json
{
  "id": "txt_0",
  "type": "text",
  "text": "SANDWICHES",      ← uses 'text' field (NOT 'content' — V1 legacy data)
  "x": 631.39,
  "y": 550.31,
  "zIndex": 10,
  "opacity": 1,
  "rotation": 0,
  "visible": true,
  "locked": false,
  "layerRole": "content",
  "style": {
    "fontFamily": "century-gothic-regular",
    "fontSize": 33.0,
    "color": "#ffffff",
    "lineHeight": 1.1,
    "letterSpacing": 0
  }
}
```

⚠️ NOTE: `style` is a nested object (`d.style.fontFamily`). The V2 schema says fields should be top-level (`d.fontFamily`). The embedded data has NOT been migrated. This is known legacy. Do NOT migrate unless explicitly asked.

### DOM Structure After render()
```
#menu-container  (onclick="onCanvasClick")
  └── #elements-layer
        └── div.editable-element.editable-text  (id="txt_0", dataset.id="txt_0")
              (innerText = "SANDWICHES")
              (contentEditable = false)
```

### Event Routing
```
User clicks text element
  → click event fires on .editable-element div
  → if attach() has el.onclick or el.onpointerdown: fires first
  → if not stopped: bubbles to #menu-container → onCanvasClick()
  → if not stopped: bubbles to #editor-viewport → onViewportClick()
```

### Key Global Variables
```javascript
let layoutLocked = false;       // true = nothing can be selected or moved
let selectedId = null;          // id string of currently selected element
let isEditingText = false;      // true = user is currently typing in a text element
let _lassoJustFired = false;    // suppresses post-lasso click clear
let _groupDragStatePushed = false;
```

### Selection Flow (Expected Correct Behavior)
```
onCanvasClick(e) OR attach(el).onpointerdown(e)
  ↓
  guard: if (_lassoJustFired) return;
  guard: if (layoutLocked) return;  ← ONLY for moving, NOT for selecting (verify this)
  ↓
  identify: id = e.target.dataset.id  (or closest .editable-element's dataset.id)
  ↓
  find element: d = docV2.elements.find(e => e.id === id)
  ↓
  if (d && !d.locked): selectedId = id; render(); updateSelectionBar();
  else: deselect();
```

### Deselect Flow (What's Accidentally Happening)
```
User clicks text element
  → selection appears for <5ms
  → something calls deselect()
  → selectedId = null; render(); hide selection bar
```

---

## ⛔ DO NOT DO THESE

1. Do NOT run `python build_app.py` — it will overwrite all live code with old code
2. Do NOT rewrite the entire `render()` function — surgical fix only
3. Do NOT change V2 schema field names (`d.text` is legacy but consistent — don't migrate)
4. Do NOT mix this fix with any other change in the same commit
5. Do NOT declare done until you confirm the SHA on GitHub via direct file read
6. Do NOT touch `app.py`, `viewer.html`, `export-utils.js`, or any other file

---

## ✅ DEFINITION OF DONE

1. Click a text element → it stays selected (yellow outline, selection bar appears)
2. Click a different text element → first deselects, second selects
3. Click empty canvas → everything deselects
4. Lasso drag-select still works (do not break commit `05e1bd6`)
5. Commit pushed, SHA confirmed by direct GitHub file read
6. Update this file's status from UNRESOLVED to RESOLVED with the commit SHA and one-line explanation of the actual fix

---

## 📁 FILES TO READ (in order)

| File | Why |
|---|---|
| `MASTER_HANDOFF.md` | Full architecture, V2 schema, non-negotiables |
| `.agents/rules/global-rules.md` | How to operate — commit rules, verification steps |
| `index.html` (GitHub direct read) | The live source. Find `attach()`, `onCanvasClick()`, `onCanvasMousedown()` |
| `EMERGENCY_DIAGNOSIS.md` | This file — don't re-read once you've read it, just fix |

---

**Last Updated:** April 9, 2026  
**Status:** 🔴 UNRESOLVED  
**Blocking:** All text editing workflows  
**Priority:** CRITICAL — this is the primary editor interaction  
