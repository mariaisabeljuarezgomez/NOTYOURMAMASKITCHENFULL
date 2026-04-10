# Menu Editor Pro V2 — Database Migration SOLUTIONS
**Status:** Unified Fix Strategy (Consolidated from Claude, Big Pickle, and Gemini)
**Date:** April 10, 2026

## 1. BUG D — Font 404s
**Discovery:** Font files (.ttf) are physically present in the repository root. The issue is purely a Flask path-routing bug.
**Solution:** 
- Update `app.py` `serve_fonts` route to use absolute pathing: `os.path.join(os.path.dirname(__file__), filename + '.ttf')`.
- Ensure standard `@font-face` declarations in `index.html` use simple filenames that match this route.

## 2. BUG A — Element Duplication
**Discovery:** A racing condition between a safety `setTimeout(..., 800)` and a `fontLoadPromise.then()` causes `doInitialRender` to fire twice.
**Solution:**
- Delete the `doInitialRender` wrapper function entirely.
- Implement a single **Waterfall Initialization** inside `window.onload`.
- Logic: `fetch (server) -> fallback (local) -> merge (_mergeLoadedDoc) -> render (exactly once)`.

## 3. BUG C — Background Flashes
**Discovery:** The `render()` loop clears all innerHTML, destroying and recreating the background element every time.
**Solution:**
- Add a dedicated `<div id="bg-layer"></div>` inside `#menu-container`, positioned below the `#elements-layer`.
- Clean background rendering logic that only updates the `src` if it has actually changed, using a `renderBackground()` function.
- Filter out background elements from the foreground `render()` loop.

## 4. BUG B — Text Interaction Failure
**Discovery:** `render()` wipes the DOM mid-interaction, losing focus/cursor state. Stale global drag handlers also interfere.
**Solution:**
- Implement an **Interaction Guard**: `if (_isDragging) return;` at the top of the `render()` function.
- Ensure `attach(el)` clears stale global handlers: `document.onmousemove = null; document.onmouseup = null;` at the start of `onmousedown`.

---

## Technical Constants confirmed for this phase:
- **Opacity Range:** 0 to 1 (per live data `opacity: 1`)
- **Git Strategy:** Must use `push_files` for `index.html` to avoid truncation.
- **Verification:** Monitor Network panel for background fetch count and 404s.
