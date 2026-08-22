# Cartly VAPI Voice Agent Backend

FastAPI + SQLite backend service tailored for **VAPI Voice Assistant Tools**.

---

## 🚀 Endpoints for VAPI Tools

| Tool Name | Method | Endpoint | Description |
|---|---|---|---|
| `Add_item` | `POST` | `/add_item` | Add or update an item on the shopping list |
| `Cancel_item` | `POST` | `/cancel_item` | Remove/cancel an item from the shopping list |
| `Item_Avilability` | `POST` | `/item_availability` | Check stock status & price for an item |
| `List_items` | `POST` | `/list_items` | List all active items grouped by category |
| `Clear_list` | `POST` | `/clear_list` | Clear all items from the shopping list |

---

## 💻 How to Run Locally

```bash
# 1. Navigate to directory
cd d:\Unthinkable\vapi-backend

# 2. Run backend server (runs on port 4444)
python backend.py
```

The server will start at: `http://127.0.0.1:4444`  
Interactive Swagger API docs available at: `http://127.0.0.1:4444/docs`

---

## 🌐 Connecting VAPI to Local Backend (via ngrok)

For VAPI to send requests to your local server:

1. Download & run ngrok:
   ```bash
   ngrok http 4444
   ```
2. Copy the generated `https://xxxx.ngrok-free.app` URL.
3. In VAPI Tool configuration, set your tool Request URLs to:
   - `Add_item`: `https://xxxx.ngrok-free.app/add_item`
   - `Cancel_item`: `https://xxxx.ngrok-free.app/cancel_item`
   - `Item_Avilability`: `https://xxxx.ngrok-free.app/item_availability`