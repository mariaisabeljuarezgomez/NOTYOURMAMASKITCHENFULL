# Investigation Report: Ephemeral Database Migration & Selection Bugs

Based on my analysis of `ephemeral_database_migration_ERRORS.md` and the current state of `index.html` and `app.py`, here is a comprehensive breakdown of the remaining active issues and the exact solutions required. **No code has been modified in generating this report.**

---

## 1. BUG A: Every Element Is Duplicated (x2) On Page Load
**Status:** **Partially Resolved, but Architecture remains fragile.**
The previous agent effectively stopped the duplication by explicitly hardcoding `docV2.elements = []` instead of baking the 97+ template elements directly into the HTML file. However, the root architectural flaw identified in the document still exists: `window.onload` executes multiple fallback paths.

**The Fix Needed:**
`window.onload` needs to be simplified into a single linear "waterfall" approach. It should attempt the `/api/menu` fetch. If that fails or returns an empty document, it should fallback to `localStorage`. Only after data is secured should `_mergeLoadedDoc(data)` be called **exactly once**, followed by `render()`. 

---

## 2. BUG B: Text Elements Are Unclickable, Uneditable, and Unmovable
**Status:** **Active & Compounded by Event Bubbling conflicts.**

There are two massive compounding issues happening on text elements right now:

### Issue 1: `onCanvasClick` vs `attach(el)` Event Bubbling Conflict
My previous agent attempted to fix this by adding `el.onclick = (e) => { e.stopPropagation(); const id = el.dataset.id || el.id; selectById(id); }` inside `attach(el)`.
While this stops the click from bubbling and successfully selects the element, it introduces a severe side effect: **It intercepts double-clicks.**
When a user double-clicks text, the browser fires `mousedown -> click -> mousedown -> click -> dblclick`. The rogue `el.onclick` handler fires twice and intercepts the sequence, often breaking the native `dblclick` event required to trigger `el.contentEditable = "true"`.

### Issue 2: `render()` Loop Destroying Active DOM Nodes
As noted in the diagnosis document, any time `render()` is called while a user is editing text or dragging an element, the DOM node is entirely destroyed (`innerHTML = ''`) and recreated. This instantly drops browser focus, stops drags mid-flight, and forces `contentEditable` back to `false`.

**The Fixes Needed:**
1. **Remove `el.onclick` entirely from `attach(el)`.**
2. **Re-add `e.stopPropagation()` inside `el.onmousedown`.**
3. **Move the selection logic strictly back to `onCanvasClick`**, but safely ignore resize handles.
   ```javascript
   function onCanvasClick(e) {
       if (_lassoJustFired || layoutLocked) return;
       // Prevent canvas click from deselecting if we just clicked a resize handle
       if (e.target.classList.contains('resize-handle')) return;
       
       const el = e.target.closest('.editable-element');
       if (el) {
           const id = el.id || el.dataset.id;
           if (id) selectById(id);
           return;
       }
       deselect();
   }
   ```
4. **Prevent redundant `render()` calls.** Operations like `selectById(id)` must never call `render()`. (Currently, `selectById` calls `renderLayerList()` which is mostly safe, but we must audit `importBackground` and `updateSelectionBar` to ensure they aren't triggering a full `render()` on simple clicks).

---

## 3. BUG C: Background Flashes On/Off Every Time Any Element Is Added
**Status:** **Active.**

The background image flickers because it is treated as a standard element inside `docV2.elements`. Every time a text box or shape is added, `render()` clears `#elements-layer` completely and rebuilds the `<img>` tag for the background. This forces the browser to re-parse the Cloudinary URL.

**The Fix Needed:**
The background must be structurally decoupled from the `render()` loop. 
1. `render()` must skip elements where `layerRole === 'background'`.
2. A separate function, `renderBackground()`, should be created. This function checks if the background URL has changed. If it hasn't, it does nothing. If it has, it updates an `<img>` tag that sits *outside* `#elements-layer` (e.g., modifying the existing `<img id="menu-bg">` directly).

---

## 4. BUG D: Font Files 404
**Status:** **Active.**

The application requests `.ttf` fonts (`century-gothic-bold.ttf`, etc.) that are no longer hosted on Railway's persistent volume.

**The Fix Needed:**
Since the font files currently live in the root of the repository (`century-gothic-bold.ttf`, etc.), `app.py` simply needs to explicitly serve them via `static_proxy` and apply aggressive `Cache-Control` headers so they load instantly after the first visit.

*(Note: The other agent actually added `if path.lower().endswith((".ttf", ".js")): response.headers["Cache-Control"] = "max-age=604800, public"` to `app.py` in commit `01109157`, so the backend support is there. The issue might be that the paths in `index.html`'s `@font-face` block do not correctly map to the root `/` path).*

---

## Final Recommendation & Next Steps
If you approve this analysis, I will:
1. Re-wire `onCanvasClick` and `attach(el)` to cleanly separate dragging, single-clicking, and double-clicking for text elements without dropping focus.
2. Decouple the background from the destructive `render()` loop to prevent the 1-second flicker.
3. Clean up the `window.onload` promise waterfall to prevent double-initialization.