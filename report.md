# Emergency Diagnosis Report: Canvas Drag & Selection Failure

## 1. The Root Cause of the Bug
The bug causes elements to briefly select for less than 5ms and then immediately deselect. This prevents any further actions like moving, resizing, or editing the text.

The failure happens during the standard browser click sequence (`mousedown` → `mouseup` → `click`):

1.  **Mousedown:** The user clicks an element (e.g., text). The `el.onmousedown` listener defined inside `attach(el)` fires immediately. It successfully finds the element's data and calls `selectById(el.id)`. The element visually appears selected (yellow outline).
2.  **Click:** A fraction of a second later, the browser fires the native `click` event. Because `e.stopPropagation()` was previously removed from `attach(el)`, the click event bubbles up to the canvas container `<div id="menu-container">`, which triggers `onCanvasClick(e)`.

Inside `onCanvasClick(e)`:
```javascript
function onCanvasClick(e) {
    if (layoutLocked) return;
    const el = e.target.closest('.editable-element');
    if (el) {
        const id = el.dataset.id; // <--- THE FATAL FLAW
        if (id) select(id);
        return;
    }
    deselect();
}
```
The function successfully locates the `.editable-element` DOM node. It then attempts to read `el.dataset.id`. **However, the `render()` loop only assigns `el.id = d.id;` when generating elements. It never assigns `el.dataset.id`.**

Because `el.dataset.id` is `undefined`, the variable `id` becomes falsy. The function skips the `if (id)` block, skips the `return`, and executes the very next line: **`deselect();`**.

This instantly wipes out the selection that `mousedown` just created, rendering the canvas unusable.

*(Note: If `id` had somehow been truthy, the code would have called `select(id)`. This would have thrown a `ReferenceError` because the correct function name is `selectById()`, but since the `if` block is always skipped, this secondary crash is never reached.)*

---

## 2. Proof (Code Snippets)
**Proof A: `onCanvasClick` assumes `dataset.id` exists and falls through to `deselect()`:**
*File: `index.html`, lines 2222-2231*
```javascript
function onCanvasClick(e) {
    if (layoutLocked) return;
    const el = e.target.closest('.editable-element');
    if (el) {
        const id = el.dataset.id; // Yields undefined
        if (id) select(id);       // Skipped
        return;                   // Skipped
    }
    deselect();                   // EXECUTES AND ERASES SELECTION!
}
```

**Proof B: The `render()` loop creates elements with `.id`, not `.dataset.id`:**
*File: `index.html`, lines ~1324-1350*
```javascript
        if (d.type === 'image') {
            el = document.createElement('div');
            el.id = d.id; // Only el.id is set, no dataset.id
            el.className = 'editable-element image-wrapper';
        // ...
        } else if (d.type === 'line') {
            el = document.createElement('div');
            el.id = d.id; // Only el.id is set
```

---

## 3. What is NOT the cause
*   **`layoutLocked` state:** Not the cause. The lock correctly reports as `false`.
*   **`isEditingText` state:** Not the cause. It is managed correctly by focus/blur events.
*   **CSS `pointer-events: none`:** Not the cause. The event successfully reaches the element (triggering the brief selection via `mousedown`) before the `click` event destroys it.
*   **`onCanvasMousedown` early return:** Not the cause. The early return (`if (e.target.closest('.editable-element')) return;`) correctly prevents the lasso from interfering with elements, which is the intended behavior.

---

## 4. The Surgical Fix (1-Line Change)
To fix this without rewriting `render()` or touching the rest of the application, change how `onCanvasClick` reads the identifier, and update the internal function call to the correct name.

**Change this inside `onCanvasClick(e)`:**
```javascript
<<<<<<< SEARCH
    if (el) {
        const id = el.dataset.id;
        if (id) select(id);
        return;
    }
=======
    if (el) {
        const id = el.id || el.dataset.id;
        if (id) selectById(id);
        return;
    }
>>>>>>> REPLACE
```

This ensures that the click handler correctly identifies the element via its standard `id` property, successfully calls the correct `selectById()` function, hits the `return;` statement, and permanently bypasses the rogue `deselect()` call.

---

## 5. Risk Assessment
*   **Impact on Dragging:** Fixing this restores dragging instantly, because elements will no longer be deselected milliseconds before a drag sequence starts.
*   **Impact on Lasso:** `onViewportClick` and `onCanvasMousedown` handle the lasso logic using separate click/mousedown paths. This change only impacts clicks directly on `.editable-element` wrappers, leaving lasso completely unaffected.
*   **Safe Fallback:** Using `el.id || el.dataset.id` ensures that if a future update ever migrates completely to `dataset.id`, the logic will still hold. Calling `selectById()` instead of `select()` prevents a hidden `ReferenceError` from crashing the execution thread.