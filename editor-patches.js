/**
 * editor-patches.js
 * Loaded after index.html inline scripts.
 * Overrides three functions that had bugs identified in code review.
 * Safe to load at any time — does not touch DOM structure.
 */

// ───────────────────────────────────────────────────────────────────────────
// FIX 1: setRpTab — correctly highlights the VIEWER tab on click.
// Manual tab stays wired to openManualModal() directly (by design).
// ───────────────────────────────────────────────────────────────────────────
function setRpTab(tab) {
    // Only 'viewer' is a real panel; 'manual' opens the modal directly.
    const panels = ['viewer'];
    panels.forEach(t => {
        const btn   = document.getElementById(`rp-tab-${t}`);
        const panel = document.getElementById(`rp-panel-${t}`);
        const isActive = t === tab;
        if (btn)   btn.classList.toggle('active', isActive);
        if (panel) panel.style.display = isActive ? 'block' : 'none';
    });
    // Ensure viewer tab stays highlighted when it is the active tab
    const viewerBtn = document.getElementById('rp-tab-viewer');
    if (viewerBtn) viewerBtn.classList.toggle('active', tab === 'viewer');
}

// ───────────────────────────────────────────────────────────────────────────
// FIX 2: saveGlobalSettings — writes viewer config into docV2.settings.viewer
// and delegates to the existing save() function.
// Eliminates: (a) race condition, (b) silent URL erase-on-reload.
// ───────────────────────────────────────────────────────────────────────────
function saveGlobalSettings() {
    const heroUrl  = (document.getElementById('hero-video-url-input')   || {}).value || '';
    const lUrl     = (document.getElementById('side-panel-left-url')    || {}).value || '';
    const lLabel   = (document.getElementById('side-panel-left-label')  || {}).value || '';
    const rUrl     = (document.getElementById('side-panel-right-url')   || {}).value || '';
    const rLabel   = (document.getElementById('side-panel-right-label') || {}).value || '';

    // Ensure the settings sub-object exists
    if (!docV2.settings) docV2.settings = {};

    // Write all viewer fields into the proper sub-object
    docV2.settings.viewer = {
        heroVideoUrl:   heroUrl,
        sidePanelLeft:  { videoUrl: lUrl,  label: lLabel },
        sidePanelRight: { videoUrl: rUrl,  label: rLabel }
    };

    // Delegate to the existing save() so viewer settings travel with the
    // main document — one save, no race condition.
    if (typeof save === 'function') {
        save();
        if (typeof showToast === 'function') showToast('\u2705 Viewer settings saved');
    }
}

// ───────────────────────────────────────────────────────────────────────────
// FIX 3: loadGlobalSettings — hydrates all 5 viewer inputs from
// docV2.settings.viewer so fields are never blank after a page reload.
// Also supports legacy top-level keys for backwards compatibility.
// Call this after load() completes.
// ───────────────────────────────────────────────────────────────────────────
function loadGlobalSettings() {
    const viewer = (docV2.settings && docV2.settings.viewer) || {};

    // Backwards compat: also check legacy top-level keys
    const heroUrl = viewer.heroVideoUrl
        || docV2.heroVideoUrl
        || '';

    const lSettings = viewer.sidePanelLeft
        || docV2.sidePanelLeft
        || {};

    const rSettings = viewer.sidePanelRight
        || docV2.sidePanelRight
        || {};

    const _set = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) el.value = val;
    };

    _set('hero-video-url-input',   heroUrl);
    _set('side-panel-left-url',    lSettings.videoUrl || '');
    _set('side-panel-left-label',  lSettings.label    || '');
    _set('side-panel-right-url',   rSettings.videoUrl || '');
    _set('side-panel-right-label', rSettings.label    || '');
}

// Auto-call on page load so inputs are populated from the saved document.
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure docV2 is fully populated by the init load()
    setTimeout(loadGlobalSettings, 1200);
});
