Complete Bug Audit — Everything Not Yet Fixed
🔴 CRITICAL — Will cause data loss or invisible breakage
BUG-C1: app.py /api/render-check has its own hardcoded asset map that diverges from viewer
app.py lines 118–134 contain a duplicate asset_map dictionary that is NOT identical to ASSET_ID_TO_SRC in viewer.html. It adds asset_014 pointing to Asset14.png AND asset_015 pointing to menu-bg-preview.jpg — neither of which exists in viewer.html's table. These two maps will always drift apart.

Fix needed: /api/render-check must resolve images by reading doc.assets from the saved JSON itself (data.get("assets", [])), not from a hardcoded map. This makes it self-consistent with whatever the editor saves.

BUG-C2: app.py validate_schema() is dangerously permissive
The save validator accepts ANY JSON that has either version+elements OR zoom+scroll+elements. This means a malformed, half-migrated, or accidentally emptied document can be saved and overwrite a good backup with no error.

Fix needed: Tighten to require version === 2 AND elements is a list. Reject version-1 documents on save (they should only be accepted on GET for migration purposes, never written back).

BUG-C3: app.py get_menu() injects a status field into the saved document before returning it
The GET route does data["status"] = status_info and returns it. If the editor ever does a GET → modify → POST cycle without stripping this field, the status object gets saved permanently into menu_data.json and rides along in every subsequent load.

Fix needed: Return status separately from the document data. Either nest as {"data": {...doc...}, "status": {...}} or strip it on the client before any save. Document this explicitly so agents don't save the status field.

BUG-C4: Upload endpoint returns only url — no assetId, no storage object
/api/upload-image returns {"status":"ok","filename":"...","url":"/Images/..."} but does NOT return an assetId or the canonical storage.originalUrl structure. The editor must construct the full asset entry from this partial response, and if it uses any different field names or generates the ID incorrectly, the asset registry and the element's assetId will not match — exactly the class of bug causing blank images.

Fix needed: The upload response must return the full structure the editor needs to build an assets entry: {"status":"ok","filename":"...","storage":{"originalUrl":"/Images/..."}}. The editor generates the UUID. The server confirms the path. Both agree on storage.originalUrl.

BUG-C5: app.py backup is skipped silently if first save has no existing file
In save_menu(), the timestamp variable is only set inside if os.path.exists(DATA_FILE). The return JSON references timestamp in a ternary — but if the file didn't exist (first ever save), timestamp is still accessed via 'timestamp' in locals(). This is fragile Python and will throw a NameError in some Python versions if the ternary evaluates incorrectly.

Fix needed: Set timestamp = None before the conditional, then set it inside the block. Remove the 'timestamp' in locals() anti-pattern.

🟠 HIGH — Causes wrong behavior that user will see
BUG-H1: Viewer poll covers only elements in hash — settings changes never trigger redraw
Already identified and in the fix plan. Confirmed in viewer.html source. The hash must cover the entire document object.

BUG-H2: app.py validate_schema() has no maximum size check
A corrupted or malicious payload of any size will be accepted and written to disk. On Railway's persistent volume, a multi-megabyte poisoned save cannot be auto-recovered without a manual restore.

Fix needed: Add if len(request.data) > 5_000_000: return jsonify({"error": "Payload too large"}), 413 before validation.

BUG-H3: /api/menu-debug is a permanent production endpoint exposing the full raw document
The comment says "Temporary debug endpoint" but it has no authentication, no removal date, and no feature flag. It returns the entire menu_data.json to anyone who hits that URL. This is the same data the editor uses.

Fix needed: Either remove it or gate it behind a secret query parameter (?key=XXXX) checked against an environment variable. Do not leave unauthenticated data exposure on a production URL.

BUG-H4: Backup directory can accumulate unbounded backups
Every save creates a timestamped backup. There is no rotation, pruning, or maximum count. On Railway's persistent volume (limited size), this will eventually fill the disk and cause save failures.

Fix needed: After writing a new backup, prune all but the most recent N (e.g. 20) backups in the backup directory.

BUG-H5: export-utils.js assumes PNG bytes always have IHDR at exactly byte offset 33
The pHYs chunk is inserted at bytes.slice(0, 33) hardcoded. This is correct for standard PNGs where the IHDR chunk always follows the 8-byte PNG signature. However, if the canvas toBlob() ever produces a PNG with an additional chunk before IHDR (non-standard but possible in some browsers), the injection will corrupt the file.

Fix needed: Before inserting, verify the IHDR chunk type signature at bytes 12–15 (bytes[12]===73 && bytes[13]===72 && bytes[14]===68 && bytes[15]===82 = "IHDR"). If not found, log a warning and insert at byte 33 anyway as fallback, but do not silently corrupt.

BUG-H6: /api/restore/<filename> has no schema validation before restoring
Any backup can be restored without checking if it is a valid V2 document. If a corrupted or V1 backup is restored, the editor will load broken data and the user may not notice until they rebuild their menu.

Fix needed: Run validate_schema() on the backup file contents before copying it to DATA_FILE. Reject with a clear error if it fails.

🟡 MEDIUM — Technical debt that creates future bugs
BUG-M1: app.py has two conflicting /Images/ routes
There is a generic static_proxy route /<path:path> AND a dedicated /Images/<path:filename> route. Flask will match the more specific route first, but the generic route also sets Cache-Control for .png files. If route resolution order ever changes or a new route conflicts, image caching behavior becomes unpredictable.

Fix needed: Remove the .png/.jpg cache-control logic from static_proxy since /Images/ has its own dedicated route that already sets the correct headers.

BUG-M2: PROTECTED_ASSETS set in app.py hardcodes Asset1–Asset14 but Asset5 does not exist
PROTECTED_ASSETS = {f"Asset{i}.png" for i in range(1, 15)} generates Asset5.png as a protected asset — but Asset5.png does not exist. RULES.md explicitly states "Asset5.png does NOT exist." This is harmless now but is a documentation-reality mismatch that will confuse future agents.

Fix needed: Replace with an explicit set: PROTECTED_ASSETS = {"Asset1.png","Asset2.png","Asset3.png","Asset4.png","Asset6.png","Asset7.png","Asset8.png","Asset9.png","Asset10.png","Asset11.png","Asset12.png","Asset13.png","Asset14.png"}.

BUG-M3: Upload endpoint does not validate file type before writing to disk
/api/upload-image accepts any base64 payload and writes it to /Images/ with whatever filename the client provides. There is no check that the data is actually an image, no MIME type validation, and no filename sanitization beyond what Python's os.path.join provides.

Fix needed: Validate that filename ends in .png, .jpg, .jpeg, or .webp. Validate that the decoded bytes start with a known image magic number (PNG: \x89PNG, JPEG: \xFF\xD8). Reject anything else with a 400.

BUG-M4: app.py comment at bottom is leftover noise
Last line: # Hardened Layers Panel & Asset Management v2.0 — this is a build artifact comment from build_app.py generation that has no meaning in the live file. While harmless, it signals to future agents that this file may have been auto-generated, which could prompt them to re-run build_app.py.

Fix needed: Remove it.

BUG-M5: export-utils.js crc32 table is rebuilt from scratch on every call
The CRC32 lookup table (256 entries) is recomputed inside crc32() every time it is called. Since inject300DpiAndDownload is only called once per export this is not a performance issue, but it is wasteful and the pattern is incorrect (table should be computed once at module load).

Fix needed: Move the table construction outside the function to module scope. Low priority but clean.

🔵 IMPORTANT FOR RULES.md — Rules that need adding
These are real behaviors discovered in app.py that RULES.md currently does not document:

/api/menu-debug exists — agents must know not to remove it without owner approval AND must know it is security-sensitive

PROTECTED_ASSETS is the delete guard — agents editing upload/delete logic must know this list governs what cannot be deleted

Backup pruning is missing — must be added as a known gap, not silently ignored

validate_schema() is the save gate — agents must not weaken it; any schema change must also update this validator

status field is injected by GET — agents must never save a document that contains the status key

Priority Order for After the Current Fix Plan
Priority	Bug	File	Risk if ignored
1	BUG-C3 status field saved into document	app.py	Silent data corruption on every save cycle
2	BUG-C1 dual diverging asset maps	app.py	render-check gives false results forever
3	BUG-C4 upload returns no storage object	app.py	Every uploaded image breaks asset registry
4	BUG-C2 permissive schema validator	app.py	Corrupt saves accepted silently
5	BUG-H3 unauthenticated debug endpoint	app.py	Public menu data exposure
6	BUG-H4 unbounded backup growth	app.py	Disk full → save failures
7	BUG-H6 restore without validation	app.py	Corrupt restore destroys good live data
8	BUG-C5 timestamp NameError risk	app.py	First-ever save may throw server error
9	BUG-H2 no payload size limit	app.py	Volume poisoning via oversized POST
10	BUG-M2 PROTECTED_ASSETS includes Asset5	app.py	Confuses agents about what exists
11	BUG-M3 no upload file type validation	app.py	Non-image files written to Images dir
12	BUG-H5 export pHYs blind insertion	export-utils.js	Rare PNG corruption on export
13	BUG-M1 dual Image route cache conflict	app.py	Future cache behavior unpredictable
14	BUG-M4 leftover build comment	app.py	Agent confusion about file origin
