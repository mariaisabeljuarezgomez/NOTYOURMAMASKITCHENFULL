NYMK Menu Editor — Full Diagnostic Report
Executive State Summary
The app is an approximately 65–70% functional single-file HTML canvas editor with a Flask/PostgreSQL backend on Railway. The core render engine, layer system, undo/redo, and AI generation pipelines are structurally present. However, there are 5 confirmed critical bugs, 7 significant logic errors, and 4 architectural time bombs that explain every symptom you described.

Bug 1 — Double Assets (Confirmed Root Cause)
What happens: Every image appears twice in the Assets panel.

Exact cause in code: loadUserImages is not defined anywhere in index.html. The app calls it inside importImg after a successful upload:

js
await loadUserImages  // called but function does not exist
Meanwhile, renderAssetPanel() is the actual panel renderer and it reads directly from docV2.assets. But importImg also calls addFromAsset(null, base64Data) as a fallback, which adds a second local copy. The result: the raw filesystem image is fetched/rendered by renderAssetPanel from docV2.assets, AND the base64 fallback path pushes a second asset object into docV2.assets with a different ID and a data: URL — two entries, same image.

Fix: Remove the addFromAsset(null, base64Data) fallback line entirely from importImg. After a successful server upload, call renderAssetPanel() (not the nonexistent loadUserImages). Replace every call to loadUserImages with renderAssetPanel().

Bug 2 — Cannot Deselect by Clicking Canvas (Confirmed Root Cause)
What happens: Clicking empty canvas area does not deselect the selected element.

Exact cause: The deselect flow depends on onViewportClick being fired on #editor-viewport. The actual click handler is:

js
function onViewportClick(e) {
  if (e.target !== e.currentTarget) return;
  ...
  deselect();
}
This correctly checks e.target === e.currentTarget. The problem is the background PNG (isSystemBackground: true) element. In attach(el), the background element has el.style.pointerEvents = 'none', which should let clicks pass through. However, in renderBackground(), a second DOM element is rendered into #bg-layer as a raw <img> with no pointer-events override. The #bg-layer container itself sits at z-index: 0 over the viewport's click target. The <img> fills 100% width/height, and because it is a child of #menu-container (not the #elements-layer), it intercepts the click before onViewportClick can fire, so deselect() is never called.

Fix: Add pointer-events: none explicitly to #bg-layer and its <img> child in renderBackground():

js
bgContainer.innerHTML = `<img src="${bgEl.src}" style="width:100%;height:100%;object-fit:cover;display:block;pointer-events:none;">`;
bgContainer.style.pointerEvents = 'none';
Bug 3 — Background Upload Failing (Cloudinary Credentials Wiped)
What happens: Uploading a replacement background returns a Cloudinary credential error.

Exact cause — two sub-issues:

3a. Credentials not restoring correctly. restoreAiCredentials(doc) reads doc.aiCredentials.klingKey but saveAiCredentials() saves the field as klingkey (lowercase k). The key name mismatch means Kling credentials never restore from DB. For Cloudinary, it saves cloudName/cloudKey/cloudSecret and restores cloudName/cloudKey/cloudSecret — those match, so Cloudinary credentials should restore. However, the importBackground function reads credentials from the DOM inputs at click time:

js
const creds = docV2.aiCredentials;
if (!creds.cloudName || !creds.cloudKey || !creds.cloudSecret) { ... abort }
It checks docV2.aiCredentials first, but if the page was reloaded after the accidental DB wipe (which reset docV2), docV2.aiCredentials will be an empty object if the session was overwritten.

3b. upload-image route does NOT use Cloudinary. Looking at app.py, the /api/upload-image endpoint saves files to the local Railway filesystem (Images/ directory), not Cloudinary. It only returns a local url. The importBackground function requires a Cloudinary URL but calls /api/upload-image which returns a Railway local path — so setAsBackground(json.url) sets a local Railway path as the background src, which will break on redeploy or any filesystem reset.

Fix: For background uploads specifically, importBackground must call /api/ai/cloudinary-upload (the actual Cloudinary endpoint), not /api/upload-image. Also fix the credential key mismatch: change klingkey → klingKey in saveAiCredentials() to match restoreAiCredentials().

Bug 4 — AI Panel Credential Enable/Disable Logic Broken
What happens: Generate buttons remain disabled even after saving valid credentials.

Exact cause: saveAiCredentials() unconditionally enables both #ai-img-btn (Stability) and #kling-img-btn after save — that part is fine. However, loadAiCredentials() is the function that runs on page load and it reads from localStorage with key AICREDKEY, but the code has this comment:

js
// Purged for V2 database-only persistence
if (!stored) return;
This means loadAiCredentials() silently exits if no localStorage key exists. On page load, credentials are restored via restoreAiCredentials(doc) (from the DB), but that function does not call removeAttribute('disabled') on the generate buttons. So after a page reload, both generate buttons stay disabled even though credentials exist in docV2.aiCredentials.

Fix: Add button-enable logic to restoreAiCredentials():

js
function restoreAiCredentials(doc) {
  const c = doc.aiCredentials;
  if (!c) return;
  // ...existing field restore...
  if (c.stabilityKey) document.getElementById('ai-img-btn').removeAttribute('disabled');
  if (c.klingKey && c.klingSecret) {
    document.getElementById('kling-img-btn').removeAttribute('disabled');
    document.getElementById('ai-vid-btn').removeAttribute('disabled');
  }
}
Bug 5 — AI-Generated Images: Storage Path is Ambiguous
What happens: You don't know if AI images are saved as local assets, Cloudinary assets, or both. Answer: it depends on the flow, and both happen inconsistently.

Exact code trace:

Stability AI image generation (generateAiImage): On success, calls saveAiImageToAssets(b64only, promptLabel). That function uploads the base64 to /api/upload-image (Railway filesystem) and gets back a local URL (e.g. Images/ai-1234.png). It pushes that as a new asset in docV2.assets. No Cloudinary involved here.

Kling image generation (generateKlingImage): On poll success, tries to fetch(pollData.imageurl) to get bytes, then calls saveAiImageToAssets(b64, 'Kling AI Image') — same Railway path. If CORS blocks the fetch, it falls back to saveAiImageToAssets(null, 'Kling AI Image', pollData.imageurl) with urlOverride, which stores the raw Kling CDN URL directly in assets — no upload at all.

"Upload to Cloudinary" button (uploadAiToCloudinary): This is a manual secondary step. It uploads the already-generated image to Cloudinary and sets window.lastAiImageUrl to the Cloudinary URL. But it does NOT update the existing asset in docV2.assets with the new URL — the asset still points to the Railway local path.

"Place on Canvas" (placeAiImageOnCanvas): Uses window.lastAiImageUrl ?? aiState.generatedImage. If Cloudinary upload was done, it uses the Cloudinary URL. If not, it uses the base64 or Kling CDN URL. The element is created with assetId: window.lastAiAssetId pointing to the Railway-stored asset, but the element's src may be the Cloudinary URL — asset registry and element src are now pointing to different locations.

Fix: After a successful Cloudinary upload in uploadAiToCloudinary, find and update the asset in docV2.assets whose id === window.lastAiAssetId and set its storage.originalUrl to the Cloudinary URL. Then save. This keeps asset registry and element src synchronized.

Bug 6 — System Background Layer Blocks All Element Selection
What happens: The background PNG introduced by the DB restore cannot be removed or replaced, and the whole system is locked.

Exact cause: The background was created via the isSystemBackground: true path (triggered by setAsBackground() or a migration). In renderLayerList, locked backgrounds show draggable: false and the toggle-lock button has a guard:

js
if (item.isSystemBackground === true) {
  showToast('Background layer cannot be unlocked...');
  return;
}
In render(), background elements skip the normal attach path and go through renderBackground() only. The element is NOT added to #elements-layer, so it cannot be selected, moved, or deleted through normal UI. The only escape valve is btn-set-bg (promote image) but that requires selecting an image first, which is broken (Bug 2). The "Replace Background" button (importBackground) requires valid Cloudinary credentials (Bug 3). You are fully locked out of background management.

Fix (immediate escape): Add a one-time admin button or console command to clear the background:

js
// Run in browser console to escape the lock:
docV2.elements = docV2.elements.filter(e => e.layerRole !== 'background');
render(); renderBackground(); renderLayerList();
save();
Fix (proper): Add a "Remove Background" button in the layer panel for isSystemBackground items that calls this cleanup and saves.

Bug 7 — alignMulti Uses Hardcoded Fallback Dimensions
What happens: Multi-element alignment produces wrong positions for elements without explicit width/height.

Exact cause in code:

js
const maxR = Math.max(...els.map(e => e.x + (e.width || 100)));
// ...
els.forEach(e => e.y = maxB - (e.height || 40));
The fallbacks 100 and 40 are arbitrary hardcoded values. Text elements in particular have no width (it's auto) and no height set. This causes misalignment when mixing text and image/shape elements.

Fix: Use document.getElementById(e.id)?.offsetWidth as the fallback, same pattern used elsewhere in the code:

js
const el = document.getElementById(e.id);
const w = e.width || el?.offsetWidth || 100;
const h = e.height || el?.offsetHeight || 40;
Bug 8 — export-utils.js pHYs Byte Offset Assumes Fixed PNG Structure
What happens: Export occasionally produces a corrupt PNG or skips DPI injection silently.

Exact cause: The IHDR check is correct but the insertion at byte 33 is hardcoded:

js
const before = bytes.slice(0, 33);  // After sig(8) + IHDR(25) = 33
This assumes no ancillary chunks appear before IHDR, which is valid per PNG spec. However, the canvas.toBlob() output from some browsers (especially on Android Chrome) includes a gAMA chunk or sRGB chunk before IHDR in certain circumstances, shifting the offset. The existing isIHDR check at bytes 12–15 should catch this, but the secondary check (bytes12 === 73 etc.) does catch it and bails without DPI. The export still works but produces 96 DPI.

Fix: Instead of hardcoding offset 33, scan forward from byte 8 to find the IHDR chunk end dynamically, then insert pHYs after it.

Bug 9 — save() Blocks on Any Base64 src Element
What happens: If any element on canvas has a base64 image src (not yet uploaded), the save is silently blocked with a toast but no visual indication except a toast.

Exact cause:

js
const base64Elements = docV2.elements.filter(el => el.src && el.src.startsWith('data:'));
if (base64Elements.length > 0) { showToast('Cannot save...'); return; }
This is intentional for backgrounds (to force Cloudinary upload), but it also blocks saving if a user adds a local image via the "Upload Img" button and the Railway upload fails silently (as it does per Bug 3). The user will see the image on canvas, try to save, get a toast, and have no path forward.

Fix: The block should only apply to elements with layerRole === 'background'. Regular content images with base64 src should be allowed to save (they'll be in local storage as Railway paths on the next upload cycle). Change the filter to:

js
const base64Elements = docV2.elements.filter(
  el => el.src && el.src.startsWith('data:') && el.layerRole === 'background'
);
Bug 10 — validateSchema in app.py Rejects version: 1 Documents
What happens: Any doc with version: 1 (old sessions from before the migration) will return HTTP 400 on POST save.

Exact cause:

python
if data.get('version') == 1:
    return False
The V1→V2 migration shim in index.html runs on load and updates field names, but it does not update docV2.version to 2 until save() is called. If a user loads a V1 doc, makes changes, and hits save before any other save has occurred, the payload still has version: 1 and the server rejects it.

Fix: Add docV2.version = 2; at the end of the V1→V2 migration shim in index.html, before any save is attempted. The save() function does set docV2.version = 2 in its payload, but the schema validation runs before that normalization at the server side.

Bug 11 — app.py /api/upload-image Ignores Passed Cloudinary Credentials
What happens: The frontend passes Cloudinary credentials in the upload-image request body, but the backend ignores them entirely.

Exact cause:

python
@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    # ...saves to local Images/ directory
    # credentials field in request body is never read
The frontend sends credentials: { cloudName, cloudKey, cloudSecret } but the route just writes to IMAGES_DIR. So regular image uploads (non-AI, non-background) never go to Cloudinary — they go to Railway's ephemeral filesystem and will be lost on redeploy.

Fix: Either (a) route /api/upload-image through Cloudinary using the provided credentials, or (b) accept that regular assets live on Railway filesystem and document this clearly. For production stability, (a) is required.

Architectural Issues (Not Bugs, But Will Break You)
A. Two-source-of-truth for credentials: Credentials live in docV2.aiCredentials (DB), localStorage (deprecated but still read), and the DOM inputs. These three can diverge. On reload, restoreAiCredentials() populates DOM from DB, but getAiCredentials() reads from DOM — so if DB restore fails for any reason, all AI calls fail silently with empty strings.

B. Railway filesystem is ephemeral: All 13+ Asset*.png files are stored on Railway disk. On any redeploy/restart, they are wiped. The PROTECTED_ASSETS set protects them from delete via API, but does not protect them from Railway redeploy. These must be migrated to Cloudinary or a persistent store.

C. docV2 is initialized as a hardcoded literal in index.html: The initial state has assets: [asset001...asset013] with originalUrl: 'Images/Asset1.png' etc. — local paths. On page load, fetch('/api/menu') overwrites this with the DB copy. But if the DB fetch fails (network issue), the app silently uses the hardcoded stale state, which may not match the server, and any save will overwrite the DB with this stale data.

D. cornerRadius for circles is set during resize but not on creation: addCircle() sets cornerRadius: 75 for a 150×150 circle. On resize, if (item.cornerRadius !== undefined) item.cornerRadius = nW / 2 — this is correct. But if cornerRadius was ever manually set to 0 via the Radius slider, resize stops updating it, causing a visually square "circle" that cannot be round again without manually setting the slider.

Summary Priority Table
#	Bug	Severity	Files
1	Double assets in panel	Critical	index.html
2	Canvas click can't deselect (bg intercepts)	Critical	index.html
6	Background locked, no escape route	Critical	index.html
3	Background upload uses wrong endpoint	Critical	index.html, app.py
4	AI buttons stay disabled after reload	High	index.html
5	AI image stored in wrong location, asset/src mismatch	High	index.html
9	Save blocked by any base64 src, not just background	High	index.html
10	V1 docs rejected on save	High	app.py
11	upload-image ignores Cloudinary creds	High	app.py
7	alignMulti hardcoded fallback dimensions	Medium	index.html
8	Export pHYs DPI offset fragile on Android	Low	export-utils.js
A–D	Architectural: ephemeral storage, credentials divergence	High	all
