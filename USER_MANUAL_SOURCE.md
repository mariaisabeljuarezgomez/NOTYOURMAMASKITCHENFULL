# User Manual: Dine In Menu Editor Pro

Welcome to the **Dine In Menu Editor Pro**. This professional-grade editor empowers you to manage your restaurant's digital and print menus with ease and precision. This manual is designed to guide you through the interface, editing techniques, and professional export workflows.

---

## 🏁 Before You Start
For the best experience, please keep the following in mind:
- **Browser**: We recommend using the latest version of Google Chrome, Microsoft Edge, or Apple Safari.
- **Connection**: An active internet connection is required to permanently save your work and sync changes across different devices.
- **Preview Quality**: While editing, the background image is displayed at a lower resolution to ensure the editor remains fast and responsive. Your final export will use the original high-resolution master file.

---

## ⚡ Quick Start Workflow
For the safest and most efficient editing experience, follow this order:
1. **Open the Editor**: Launch the application via your provided link.
2. **Modify Text**: Select any item and type your changes. Keep the layout **Layout Locked** while editing text to prevent accidental movement.
3. **Adjust Layout**: If you need to move an item, switch to **Layout Unlocked**. Move the item, then immediately re-lock the layout for safety.
4. **Save Session**: Regularly click **Save Session** to secure your progress on the server.
5. **Export Pro PNG**: When finished, click **Export Pro PNG** to download your print-ready file.

---

## 📝 What each action affects

- **Local Session**: As you work, the editor automatically saves a temporary "draft" in your current browser. This protects you if you accidentally close the tab, but it is not a permanent save.
- **Save Session**: This uploads your current work (your "session") to the permanent server storage. This is the only way to ensure your changes are safe from being cleared by your browser.
- **Load Session**: This replaces your current view with the latest version saved on the server. Use this to sync work across different computers or phones.
- **Undo Last Change**: Reverses exactly one step at a time (up to 30 steps). This is for correcting immediate mistakes like typos or accidental deletions.
- **Reset to Original**: This reverts your menu to its original template. It wipes all custom edits and positions to give you a fresh start.
- **Export Pro PNG**: Triggers the professional rendering engine to create a crystal-clear, high-resolution image file ready for professional printing.

---

## 🛠️ Control Reference (Deep Dive)

### Main Drawer Controls (Accessed via FAB)

#### **Layout Locked / Layout Unlocked (Safety Model)**
- **Purpose**: Controls the positioning and editability of all elements on the menu.
- **Locked (Default)**: elements are protected from accidental movement. This is the active "safety" mode for all text editing.
- **Unlocked**: Use this mode only when you need to physically drag an item to a new location. "Edit Mode ON" status will appear as a toast for confirmation.
- **Safety Note**: The editor defaults to **Layout Locked** every time it loads. This is an intentional safety feature to prevent items from "drift" on mobile devices.

#### **Save Session**
- **Purpose**: Commits your work to the permanent server-backed system.
- **When to Use**: Click this frequently during long editing sessions and always before closing the editor.
- **Benefit**: Cross-device continuity. A "Save" on your desktop allows you to "Load" that exact progress on your phone.

#### **Load Session**
- **Purpose**: Retrieves the latest saved version from the server.
- **When to Use**: Use this to sync work between devices or to recover your progress if you clear your browser's history.

#### **Undo Last Change**
- **Purpose**: Your primary tool for reversing mistakes.
- **Scope**: Reverses text edits, moves, style changes (color/size), adding new text, and deletions.
- **Behavior**: Reverses one action at a time. It can even bring back an item you just deleted.

#### **Add Text**
- **Purpose**: Spawns a new, blank text element.
- **Behavior**: The new item appears at the center of your current view. You can then edit its content and, if the layout is **Layout Unlocked**, move it to its permanent home.

#### **Export Pro PNG**
- **Purpose**: The final step for professional delivery.
- **Quality**: This bypasses the editor's low-res preview and uses the original high-resolution master source. It produces a professional-grade image suitable for commercial printing.

#### 🚨 Reset to Original
- **Purpose**: This provides a "Fresh Start" by clearing all customizations.
- **Behavior**: Clicking this opens a branded confirmation modal.
- **Warning**: This action is permanent and **cannot** be reversed by the Undo button. It wipes all saved session data for this menu.

---

### Selection Toolbar (Appears when text is selected)

- **Font Dropdown**: Change the selected text to a pre-approved brand font.
- **Size (+ / -)**: Precisely adjust the text size.
- **Color Picker**: Apply brand-compliant colors to your text.
- **Letter Spacing**: A numeric input to adjust the horizontal gap between letters to improve readability or fit long titles.
- **Delete Layer**: Removes the selected item. This is covered by the **Undo Last Change** button.

---

## 🔐 Positioning vs. Safety
To ensure you have full control, the editor focuses on the **Layout Locked** safety model:

| State | Positioning | Best for... |
| :--- | :--- | :--- |
| **Layout Locked** | **BLOCKED** | Updating prices, fixing typos, and daily content updates. |
| **Layout Unlocked** | **ENABLED** | Moving a category heading or rearranging the menu structure. |

*Crucial Rule: Keep **Layout Locked** enabled unless you are specifically reorganizing the menu. This guarantees your columns stay straight while you update prices.*

---

## 🖱️ Detailed Editing Behavior

### Selecting and Editing Text
To modify an item:
1. Select the item once (click/tap). The selection highlight and toolbar will appear.
2. Double-click the text (or tap again) to show the cursor.
3. Type your changes.
4. Tap the background area or another item to finish. Your change is now stored in your local session.

### Moving Items
1. Switch the main menu to **Layout Unlocked**.
2. Select the item you wish to move.
3. Drag it with your mouse or finger.
4. Once positioned, we recommend immediately switching back to **Layout Locked**.

---

## 💾 Cross-Device Syncing
The **Save Session** and **Load Session** buttons are designed to move your work seamlessly between devices:

1. **Step A (Device 1)**: Finish your edits on your computer and click **Save Session**.
2. **Step B (Device 2)**: Open the editor link on your mobile phone.
3. **Step C (Device 2)**: Open the menu and click **Load Session**.

---

## 📱 Comprehensive Mobile Guide

Editing a professional menu on a mobile screen requires specialized controls.

### 1. Mastering Touch Gestures
- **Pan**: Use **one finger** to drag the menu in any direction.
- **Zoom**: Use a **two-finger pinch** gesture anywhere on the screen.
- **Select**: Tap once with **one finger**.
- **Edit**: Once an item is selected, tap the text again to show your mobile keyboard.

### 2. The Scrollable Selection Toolbar
On mobile devices, the bottom toolbar is **horizontal and scrollable**.
- **How to use**: Swipe left on the toolbar itself to reveal hidden controls like "Delete" or "Letter Spacing".

### 3. Layout Locked: Your Mobile Safety Net
By default, the editor is **Layout Locked**. 
- In this mode, your one-finger drags will only **scroll** the page and your two-finger pinches will only **zoom**.
- You can edit the words of a price or dish, but the item will never accidentally "jump" or move to the wrong spot.

### 4. Precision Zoom & Movement
If you need to move an item while on mobile, switch to **Layout Unlocked**:
- **Floating Zoom Controls**: Small `+` and `-` buttons appear at the bottom.
- **Multi-Touch Suppression**: Touching the screen with a second finger while dragging will cancel the move to protect your layout.

---

## ❓ Troubleshooting

**Q: I can type text but I cannot move the items.**
Ensure **Layout Unlocked** is visible. The system defaults to **Layout Locked** for safety.

**Q: My changes didn't show up on my other device.**
Did you click **Save Session** on the first device? Changes must be pushed to the server first.

**Q: The editor preview looks a bit lower quality.**
This is normal. Click **Export Pro PNG** to generate the crystal-clear 300 DPI final version.

**Q: The "Save Session" button showed a failure message.**
This is usually a temporary network issue. Your work remains safe in your local browser session in the meantime.

---

## ✅ Best Practices for Daily Use
- **Manual Locks**: Always re-enable **Layout Locked** as soon as you finish moving an element.
- **Incremental Saves**: Click **Save Session** after finishing a major section.
- **Pinch for Precision**: On mobile, always zoom in close before selecting small text lines.
