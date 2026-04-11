---
trigger: always_on
---

⛔ MANDATORY: READ AND CONFIRM THESE RULES BEFORE DOING ANYTHING ELSE

Before you write a single line of code, before you make any suggestion, before you do anything — you must read and explicitly acknowledge each rule below by number. Do not proceed until you have stated "I confirm rule 1, I confirm rule 2..." through all rules. If you skip this acknowledgment, your response will be rejected.

RULE 1 — READ THE LIVE FILES FIRST.
Fetch the current live versions of all relevant files from GitHub before doing anything. Do not use cached versions, do not use what was pasted in a previous message, do not reconstruct from memory. Confirm the SHA of each file you read.

RULE 2 — THIS SESSION IS READ-ONLY UNLESS EXPLICITLY TOLD OTHERWISE.
You are in AUDIT/ANALYSIS MODE. You make zero commits, zero pushes, zero file changes unless Rogelio types the exact words "YOU ARE CLEARED TO COMMIT" in this session. If you are unsure whether you are cleared, you are not cleared.

RULE 3 — NO FORCE PUSH. EVER.
git push --force is permanently banned on this repository. It has already caused irreversible data loss. If you even suggest it, this session ends.

RULE 4 — NO DB SCHEMA CHANGES WITHOUT EXPLICIT WRITTEN APPROVAL.
The sessions table schema is: id TEXT PRIMARY KEY, canvas_json JSONB, updated_at TIMESTAMP. Do not add columns, rename columns, alter types, or suggest any migration unless Rogelio approves the exact SQL first in this session.

RULE 5 — NEVER OVERWRITE THE main SESSION RECORD.
The main record in the sessions table contains Rogelio's live menu data. Do not seed it, reset it, or overwrite it for any reason. ON CONFLICT DO NOTHING is the only acceptable behavior in init_db().

RULE 6 — NO UNAUTHORIZED CHANGES.
Only change exactly what was asked. Do not improve, refactor, clean up, or optimize anything not explicitly requested. Every unauthorized "improvement" has broken this app.

RULE 7 — NO GUESSING ON FIELD NAMES.
If you are unsure whether a field is d.text or d.content, borderColor or strokeColor, cornerRadius or borderRadius — you stop and ask. You do not pick one and proceed. Guessed field names silently break the editor.

RULE 8 — REPORT HONESTLY.
If something is broken, say it is broken. If data was lost, say data was lost. Do not tell Rogelio his data is safe unless you have directly queried the database and verified the contents. Lies and false reassurances have caused more damage than the bugs themselves.

RULE 9 — ONE CHANGE AT A TIME.
If you find other bugs while working on the assigned task, you report them separately. You do not fix them silently. You do not bundle fixes.

RULE 10 — UPDATE MASTER_HANDOFF.md WITH EVERY CODE CHANGE.
Every commit must include a MASTER_HANDOFF.md update. No exceptions. An undocumented change is an incomplete change.

NOW STATE YOUR CONFIRMATION OF ALL 10 RULES BEFORE PROCEEDING.
Format: "I confirm Rule 1: [restate it in your own words]. I confirm Rule 2: ..." and so on through Rule 10.
If you do not do this, your response will be rejected and the session will restart.

