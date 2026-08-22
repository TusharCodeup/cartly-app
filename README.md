# Cartly — Voice Command Shopping Assistant

Cartly is a voice-first, smart grocery shopping assistant built for hands-free list management. It pairs real-time Web Speech recognition with a text-command fallback, smart substitute suggestions, price filtering, and VAPI custom tool backend integrations.

---

## ✨ Features

- 🎙️ **Voice-First Input & Text Fallback** — Real-time microphone listening via Web Speech API with dual-layer regex & AI intent parsing.
- 🔊 **Audio Voice Confirmations** — Spoken Text-to-Speech confirmations out loud (`window.speechSynthesis`).
- ⚡ **VAPI Custom Tool Integrations** — FastAPI backend endpoints for `/add_item`, `/cancel_item`, `/item_availability`, `/list_items`, and `/clear_list`.
- 🛍️ **Storefront UI & Smart Suggestions** — Product catalog, seasonal picks, replenishment alerts, and healthy dietary substitute swaps.
- 🌐 **Multilingual Support** — Command recognition across English, Spanish, Hindi, French, German, and Portuguese.

---

## 🛠️ Tech Stack

- **Frontend:** HTML5, React 18, Tailwind CSS, Lucide Icons, Web Speech API
- **Backend:** Python 3.11, FastAPI, Uvicorn, SQLAlchemy, SQLite
- **Voice Agent Tools:** VAPI Custom Tools Integration (`POST /vapi/tools`)

---

## 🚀 How to Run Locally

### 1. Run FastAPI Backend (Port 4444)
```bash
cd vapi-backend
python backend.py
```
*API Swagger Docs available at:* `http://localhost:4444/docs`

### 2. Open Storefront Web App
Simply open `index.html` in your browser or run a local HTTP server:
```bash
python -m http.server 8080
```
*App live at:* `http://localhost:8080`
