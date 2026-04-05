# Not Your Mama's Kitchen - Menu Editor Pro

This repository contains the high-performance, mobile-optimized menu editor for "Not Your Mama's Kitchen".

## 🚀 One-Click Deployment to Railway

This project is pre-configured for **Railway**.
1. Connect your GitHub repository to Railway.
2. Railway will automatically detect the `app.py` and `Procfile`.
3. Your site will be live at a custom Railway URL!

## 🛠 Local Development

To make changes locally:
1.  **Edit Content**: Run `python build_app.py` after modifying any coordinates or assets to regenerate the `index.html`.
2.  **Test Locally**: Run `python app.py` and visit `http://localhost:5000`.

## 📁 Project Structure

- `index.html`: The final, self-contained application (contains all fonts and images).
- `build_app.py`: The Python script that generates the `index.html`.
- `app.py`: A lightweight server to host the site online.
- `MASTER_TECHNICAL_SPEC.md`: Detailed documentation of the project architecture and fixes.

## 📱 Mobile Optimized
- Featuring vibrant orange scrollbars and a pulsing "Scroll for more" hint.
- Perfect canvas-style zooming and panning for easy editing on any screen size.

<!-- test: volume persistence verified 2026-04-05 -->
