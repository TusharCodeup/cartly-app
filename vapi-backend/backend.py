"""
Cartly Voice Agent Backend
---------------------------
Serves two callers:
  1. VAPI, via POST /vapi/tools -- receives the {"message": {"toolCallList": [...]}}
     envelope VAPI actually sends, and must reply {"results": [{"toolCallId", "result"}]}
     with `result` as a single-line string. (Flat per-tool Pydantic bodies, as in the
     original version of this file, don't match what VAPI posts -- this was the main
     correctness gap in the previous version.)
  2. The Cartly web frontend, via plain REST (GET /items, GET /replenishment, etc.)
     returning normal JSON.

Both paths share the same handler functions and the same database, so a caller's
voice-added items show up instantly in the web view for the same session_id.
"""
import datetime as dt
import hmac
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from database import ShoppingItem, get_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cartly")

init_db()

app = FastAPI(
    title="Cartly Voice Agent Backend",
    description="API backend for the Cartly voice shopping assistant (VAPI tools + web frontend).",
    version="2.0.0",
)

# ---- CORS -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- auth for the VAPI webhook ----------------------------------------
# Configure a "Secret Token" (or equivalent) for this tool's server URL in
# the VAPI dashboard, set the same value here, and confirm which header
# name your VAPI account actually sends it as -- this has been x-vapi-secret
# in VAPI's docs, but double-check the dashboard, since tool-auth config
# has changed shape before. Leave VAPI_TOOL_SECRET unset for local dev only.
VAPI_TOOL_SECRET = os.environ.get("VAPI_TOOL_SECRET", "")
VAPI_SECRET_HEADER = os.environ.get("VAPI_SECRET_HEADER_NAME", "x-vapi-secret")


async def verify_vapi_request(request: Request):
    if not VAPI_TOOL_SECRET:
        logger.warning("VAPI_TOOL_SECRET is not set -- /vapi/tools is UNAUTHENTICATED. Do not deploy like this.")
        return
    incoming = request.headers.get(VAPI_SECRET_HEADER, "")
    if not hmac.compare_digest(incoming, VAPI_TOOL_SECRET):
        raise HTTPException(status_code=401, detail="Invalid tool secret")


# -------------------------------------------------------------
# Reference data (kept consistent with the Cartly knowledge base
# and storefront so the whole system agrees with itself)
# -------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "Produce": ["apple", "banana", "orange", "grape", "strawberry", "tomato", "potato", "onion", "garlic", "spinach", "lettuce", "broccoli", "carrot", "avocado", "corn", "berry"],
    "Dairy": ["milk", "butter", "cheese", "yogurt", "cream", "egg", "cheddar", "mozzarella", "brie", "ghee"],
    "Bakery": ["bread", "roll", "bun", "bagel", "muffin", "cake", "cookie", "tortilla", "croissant", "loaf", "sourdough"],
    "Beverages": ["water", "juice", "coffee", "tea", "soda", "wine", "beer", "lemonade", "sparkling", "drink", "brew"],
    "Pantry": ["rice", "pasta", "flour", "sugar", "salt", "oil", "honey", "sauce", "bean", "cereal", "noodle", "spice", "ketchup", "mayo"],
    "Snacks": ["chip", "popcorn", "nut", "chocolate", "candy", "cracker", "biscuit", "snack", "pretzel", "gummy"],
    "Household": ["soap", "shampoo", "toothpaste", "detergent", "tissue", "paper", "cleaner", "towel", "sponge", "bleach", "foil"],
    "Meat": ["chicken", "beef", "pork", "turkey", "fish", "salmon", "tuna", "shrimp", "bacon", "steak", "sausage", "ham", "tofu"],
}

# Same substitution logic documented in the Cartly knowledge base -- one
# suggestion per item, offered once, from a fixed table (not a live model).
SUBSTITUTES = {
    "whole milk": "oat milk", "milk": "oat milk",
    "white sugar": "coconut sugar", "sugar": "honey",
    "regular pasta": "gluten-free pasta", "pasta": "gluten-free pasta",
    "white bread": "whole wheat bread", "bread": "whole wheat bread",
    "white rice": "brown rice", "rice": "brown rice",
    "butter": "plant-based margarine",
    "regular yogurt": "greek yogurt", "yogurt": "greek yogurt",
    "ground beef": "plant-based ground \"meat\"",
    "mayonnaise": "avocado spread", "mayo": "avocado spread",
    "potato chips": "baked veggie chips", "chips": "baked veggie chips",
    "soda": "sparkling water",
}

# Mock stock/pricing, same spirit as the original -- there's no real
# retailer behind this. Swap for a real catalog/inventory API when ready.
AVAILABILITY_CATALOG = {
    "oat milk": 4.99, "almond milk": 4.79, "milk": 3.79, "sourdough": 4.99, "bread": 4.99,
    "eggs": 3.49, "egg": 3.49, "strawberries": 4.49, "strawberry": 4.49, "apples": 1.29, "apple": 1.29,
    "chicken": 9.99, "salmon": 13.49, "bananas": 0.59, "banana": 0.59, "pasta": 2.49,
    "toothpaste": 3.99, "tofu": 2.79, "avocados": 1.49, "avocado": 1.49, "spinach": 3.29,
    "water": 5.99, "rice": 7.99, "olive oil": 9.49, "honey": 6.29, "yogurt": 5.49,
}
OUT_OF_STOCK = {"dragonfruit", "caviar", "truffle", "fresh lobster", "wasabi root"}


def detect_category(item_name: str, given: Optional[str] = None) -> str:
    if given and given != "Other":
        return given
    lower = item_name.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return cat
    return "Other"


def find_substitute(item_name: str) -> Optional[str]:
    lower = item_name.lower()
    for key in sorted(SUBSTITUTES, key=len, reverse=True):  # longest key first
        if key in lower:
            return SUBSTITUTES[key]
    return None


def normalize_name(raw: str) -> str:
    """Lowercase + collapse whitespace + naive singularize, for matching --
    NOT for display. 'Bottles of Milk ' and 'bottle of milk' -> 'bottle of milk'.
    Deliberately conservative (won't strip 's' from short/'-ss' words)."""
    s = re.sub(r"\s+", " ", raw.strip().lower())
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s


def format_qty(q: float) -> str:
    return str(int(q)) if q == int(q) else f"{q:g}"


def qty_phrase(q: float, unit: Optional[str]) -> str:
    return f"{format_qty(q)} {unit}".strip() if unit else format_qty(q)


def speak_item(q: float, unit: Optional[str], name: str) -> str:
    return f"{qty_phrase(q, unit)} {name}".strip()


# -------------------------------------------------------------
# Argument schemas -- validate the *unwrapped* tool arguments,
# not the raw HTTP body (see extract_tool_calls below)
# -------------------------------------------------------------

class AddItemArgs(BaseModel):
    itemName: str
    quantity: float = Field(default=1.0, gt=0, le=100)
    unit: Optional[str] = ""
    category: Optional[str] = None
    maxPrice: Optional[float] = Field(default=None, ge=0)


class ModifyItemArgs(BaseModel):
    itemName: str
    quantity: float = Field(..., gt=0, le=100)
    unit: Optional[str] = None


class CancelItemArgs(BaseModel):
    itemName: str


class SearchItemsArgs(BaseModel):
    query: Optional[str] = ""
    maxPrice: Optional[float] = Field(default=None, ge=0)


class AvailabilityArgs(BaseModel):
    itemName: str


# -------------------------------------------------------------
# Handlers -- pure(ish) functions: (db, session_id, args) -> spoken string.
# Every return value is a single-line string, per VAPI's requirement that
# `result` not be an object/array and contain no line breaks.
# -------------------------------------------------------------

def _active_query(db: Session, session_id: str):
    return db.query(ShoppingItem).filter(ShoppingItem.session_id == session_id, ShoppingItem.canceled == False)


def handle_add_item(db: Session, session_id: str, args: dict) -> str:
    parsed = AddItemArgs(**args)
    norm = normalize_name(parsed.itemName)
    category = detect_category(parsed.itemName, parsed.category)

    existing = _active_query(db, session_id).filter(ShoppingItem.normalized_name == norm).first()

    if existing:
        existing.quantity += parsed.quantity
        if parsed.unit:
            existing.unit = parsed.unit
        if parsed.maxPrice is not None:
            existing.max_price = parsed.maxPrice
        db.commit()
        result = f"Updated {existing.name} to {qty_phrase(existing.quantity, existing.unit)}"
    else:
        item = ShoppingItem(
            session_id=session_id, name=parsed.itemName.strip(), normalized_name=norm,
            quantity=parsed.quantity, unit=parsed.unit or "", category=category, max_price=parsed.maxPrice,
        )
        db.add(item)
        db.commit()
        result = f"Added {speak_item(parsed.quantity, parsed.unit, parsed.itemName)} to {category}"

    sub = find_substitute(parsed.itemName)
    if sub:
        result += f". Some people swap this for {sub} -- want me to use that instead?"
    return result


def handle_modify_item(db: Session, session_id: str, args: dict) -> str:
    parsed = ModifyItemArgs(**args)
    norm = normalize_name(parsed.itemName)
    existing = _active_query(db, session_id).filter(ShoppingItem.normalized_name == norm).first()

    if not existing:
        item = ShoppingItem(
            session_id=session_id, name=parsed.itemName.strip(), normalized_name=norm,
            quantity=parsed.quantity, unit=parsed.unit or "", category=detect_category(parsed.itemName),
        )
        db.add(item)
        db.commit()
        return f"'{parsed.itemName}' wasn't on your list yet, so I added {speak_item(parsed.quantity, parsed.unit, parsed.itemName)}"

    existing.quantity = parsed.quantity
    if parsed.unit:
        existing.unit = parsed.unit
    db.commit()
    return f"Updated {existing.name} to {qty_phrase(existing.quantity, existing.unit)}"


def handle_cancel_item(db: Session, session_id: str, args: dict) -> str:
    parsed = CancelItemArgs(**args)
    norm = normalize_name(parsed.itemName)

    exact = _active_query(db, session_id).filter(ShoppingItem.normalized_name == norm).all()
    if exact:
        for item in exact:
            item.canceled = True
            item.canceled_at = dt.datetime.utcnow()
        db.commit()
        return f"Removed {', '.join(i.name for i in exact)} from your list"

    # No exact match: offer close matches instead of guessing and deleting
    # the wrong item (the previous version's `ilike('%term%')` cancel could
    # wipe out "pineapple" when asked to remove "apple").
    close = _active_query(db, session_id).filter(ShoppingItem.normalized_name.contains(norm)).all()
    if close:
        options = ", ".join(i.name for i in close)
        return f"I didn't find '{parsed.itemName}' exactly -- did you mean {options}? Tell me which one to remove."

    return f"'{parsed.itemName}' isn't on your list"


def handle_search_items(db: Session, session_id: str, args: dict) -> str:
    parsed = SearchItemsArgs(**args)
    q = (parsed.query or "").strip()
    query = _active_query(db, session_id)
    if q:
        query = query.filter(ShoppingItem.normalized_name.contains(normalize_name(q)))
    if parsed.maxPrice is not None:
        query = query.filter((ShoppingItem.max_price.is_(None)) | (ShoppingItem.max_price <= parsed.maxPrice))
    items = query.all()

    if not items:
        return f"No items on your list match '{q}'" if q else "Your list is empty"
    return f"Found: {', '.join(speak_item(i.quantity, i.unit, i.name) for i in items)}"


def handle_item_availability(db: Session, session_id: str, args: dict) -> str:
    parsed = AvailabilityArgs(**args)
    lower = parsed.itemName.lower()

    if any(oos in lower for oos in OUT_OF_STOCK):
        return f"Sorry, {parsed.itemName} is out of stock right now"

    price = next((p for k, p in sorted(AVAILABILITY_CATALOG.items(), key=lambda kv: -len(kv[0])) if k in lower), 3.99)
    return f"{parsed.itemName.capitalize()} is in stock, around ${price:.2f}"


def handle_list_items(db: Session, session_id: str, args: dict) -> str:
    items = _active_query(db, session_id).order_by(ShoppingItem.category).all()
    if not items:
        return "Your list is empty"
    listed = ", ".join(speak_item(i.quantity, i.unit, i.name) for i in items)
    return f"Your list has {len(items)} item{'s' if len(items) != 1 else ''}: {listed}"


def handle_clear_list(db: Session, session_id: str, args: dict) -> str:
    items = _active_query(db, session_id).all()
    count = len(items)
    for i in items:
        i.canceled = True
        i.canceled_at = dt.datetime.utcnow()
    db.commit()
    return f"Cleared {count} item{'s' if count != 1 else ''} from your list" if count else "Your list was already empty"


def compute_replenishment(db: Session, session_id: str, min_cycles: int = 2, threshold: float = 0.85) -> List[Tuple[str, float, float]]:
    """
    Heuristic, not a forecasting model -- and deliberately so: it only uses
    a caller's own history, needs no external data, and its reasoning is
    inspectable (a real interval compared to a real gap), which matters for
    a feature that will speak its suggestions out loud.

    For each item name: look at how often it has historically been re-added
    (average days between add events). If the most recent instance is
    currently canceled (i.e. not on the list right now) and it's been at
    least `threshold` x that average gap since it was removed, flag it.
    """
    rows = db.query(ShoppingItem).filter(ShoppingItem.session_id == session_id).order_by(ShoppingItem.normalized_name, ShoppingItem.created_at).all()

    by_name: Dict[str, List[ShoppingItem]] = {}
    for r in rows:
        by_name.setdefault(r.normalized_name, []).append(r)

    now = dt.datetime.utcnow()
    results = []
    for _, history in by_name.items():
        if len(history) < min_cycles:
            continue
        last = history[-1]
        if not last.canceled:
            continue  # currently on the list -- nothing to nudge about

        gaps = [(b.created_at - a.created_at).total_seconds() / 86400 for a, b in zip(history, history[1:])]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        if avg_gap <= 0:
            continue

        removed_at = last.canceled_at or last.created_at
        days_since_removed = (now - removed_at).total_seconds() / 86400
        if days_since_removed >= avg_gap * threshold:
            results.append((last.name, avg_gap, days_since_removed))
    return results


def handle_replenishment_suggestions(db: Session, session_id: str, args: dict) -> str:
    suggestions = compute_replenishment(db, session_id)
    if not suggestions:
        return "Nothing looks like it needs replenishing yet"
    listed = "; ".join(f"{name} (usually every {round(gap)} days, it's been {round(since)})" for name, gap, since in suggestions)
    return f"You might be running low on: {listed}"


TOOL_HANDLERS = {
    "add_item": handle_add_item,
    "Add_item": handle_add_item,
    "BASKET": handle_add_item,
    "basket": handle_add_item,
    "modify_item": handle_modify_item,
    "update_item": handle_modify_item,
    "cancel_item": handle_cancel_item,
    "Cancel_item": handle_cancel_item,
    "remove_item": handle_cancel_item,
    "search_items": handle_search_items,
    "item_availability": handle_item_availability,
    "Item_Avilability": handle_item_availability,
    "Item_Availability": handle_item_availability,
    "list_items": handle_list_items,
    "clear_list": handle_clear_list,
    "replenishment_suggestions": handle_replenishment_suggestions,
}


# -------------------------------------------------------------
# VAPI envelope handling
# -------------------------------------------------------------

def extract_tool_calls(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """VAPI's schema has had more than one shape in the wild (toolCallList vs
    the older toolCalls; arguments nested under .function vs flattened; and
    arguments arriving as either a dict or a JSON-encoded string). Handle
    all of them rather than assuming one -- log a raw payload from your own
    dashboard's test call once and confirm which shape you're actually on."""
    message = payload.get("message", {}) or {}
    raw_calls = message.get("toolCallList") or message.get("toolCalls") or []

    calls = []
    for raw in raw_calls:
        call_id = raw.get("id")
        fn = raw.get("function") or {}
        name = fn.get("name") or raw.get("name")
        args = fn.get("arguments", None)
        if args is None:
            args = raw.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        calls.append({"id": call_id, "name": name, "arguments": args or {}})
    return calls


def get_session_id(payload: Dict[str, Any]) -> str:
    """Every VAPI call carries a stable call id in message.call.id -- use it
    to scope the list per caller automatically, without relying on the LLM
    to remember to pass a session id as a tool argument."""
    message = payload.get("message", {}) or {}
    call = message.get("call") or {}
    if call.get("id"):
        return str(call["id"])
    customer = message.get("customer") or {}
    if customer.get("number"):
        return f"phone:{customer['number']}"
    return "default"


@app.post("/vapi/tools")
async def vapi_tools(request: Request, db: Session = Depends(get_db), _auth=Depends(verify_vapi_request)):
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return {"results": []}

    session_id = get_session_id(payload)
    calls = extract_tool_calls(payload)

    results = []
    for call in calls:
        handler = TOOL_HANDLERS.get(call["name"])
        try:
            if handler is None:
                text = f"Tool '{call['name']}' isn't implemented on this server"
            else:
                text = handler(db, session_id, call["arguments"])
        except ValidationError:
            db.rollback()
            text = "I didn't quite catch the item or quantity for that -- could you say it again?"
        except Exception:
            db.rollback()
            logger.exception("Tool call failed: %s", call.get("name"))
            text = "Something went wrong on my end -- mind trying that again?"
        results.append({"toolCallId": call["id"], "result": text})

    # Always HTTP 200: VAPI ignores any other status code entirely, so a
    # non-200 here wouldn't surface as a spoken error -- it would just look
    # like a dropped tool call.
    return {"results": results}


# -------------------------------------------------------------
# Plain REST for the Cartly web frontend (unwrapped JSON)
# -------------------------------------------------------------

def to_dto(item: ShoppingItem) -> dict:
    return {
        "id": getattr(item, "id", 0),
        "itemName": getattr(item, "name", ""),
        "quantity": getattr(item, "quantity", 1.0) or 1.0,
        "unit": getattr(item, "unit", "") or "",
        "category": getattr(item, "category", "Other") or "Other",
        "maxPrice": getattr(item, "max_price", None),
        "checked": bool(getattr(item, "checked", False)),
    }


@app.get("/")
def root():
    return {
        "status": "online",
        "system": "Cartly Voice Agent Backend",
        "version": "2.0.0",
        "vapi_webhook": "/vapi/tools",
        "frontend_endpoints": ["/items", "/replenishment"],
    }


@app.post("/list_items")
@app.get("/list_items")
@app.get("/items")
def get_items(session_id: str = "default", db: Session = Depends(get_db)):
    try:
        items = _active_query(db, session_id).order_by(ShoppingItem.category).all()
        return {"count": len(items), "items": [to_dto(i) for i in items]}
    except Exception as e:
        logger.exception("Database query error in get_items, attempting auto-repair: %s", str(e))
        db.rollback()
        try:
            init_db()
            items = _active_query(db, session_id).order_by(ShoppingItem.category).all()
            return {"count": len(items), "items": [to_dto(i) for i in items]}
        except Exception:
            return {"count": 0, "items": []}


@app.get("/replenishment")
def get_replenishment(session_id: str = "default", db: Session = Depends(get_db)):
    suggestions = compute_replenishment(db, session_id)
    return {
        "suggestions": [
            {"name": name, "typical_interval_days": round(gap, 1), "days_since_removed": round(since, 1)}
            for name, gap, since in suggestions
        ]
    }


# -------------------------------------------------------------
# Flat JSON & GET/POST API routes (for VAPI tool calls & web frontend)
# -------------------------------------------------------------

@app.api_route("/{tool_name}", methods=["GET", "POST"])
@app.api_route("/dev/{tool_name}", methods=["GET", "POST"])
async def call_tool_route(
    tool_name: str,
    request: Request,
    args: Optional[Dict[str, Any]] = None,
    session_id: str = "default",
    db: Session = Depends(get_db)
):
    if tool_name in ["items", "replenishment", "vapi"]:
        raise HTTPException(status_code=404, detail="Reserved endpoint")

    handler = TOOL_HANDLERS.get(tool_name) or TOOL_HANDLERS.get(tool_name.lower()) or TOOL_HANDLERS.get(tool_name.capitalize())
    if handler is None:
        raise HTTPException(status_code=404, detail=f"No handler named '{tool_name}'")

    merged_args: Dict[str, Any] = {}

    # Extract GET query parameters
    query_params = dict(request.query_params)
    for k, v in query_params.items():
        # normalize snake_case keys from VAPI (item_name -> itemName)
        norm_k = k
        if k == "item_name": norm_k = "itemName"
        elif k == "max_price": norm_k = "maxPrice"
        merged_args[norm_k] = v

    # Extract POST JSON body if available
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                for k, v in body.items():
                    merged_args[k] = v
        except Exception:
            pass

    if args:
        merged_args.update(args)

    # Universal parameter normalization
    if "itemName" not in merged_args or not merged_args["itemName"]:
        for alt_key in ["item_name", "item", "name", "product", "food", "text", "query", "q", "title"]:
            if alt_key in merged_args and merged_args[alt_key]:
                merged_args["itemName"] = str(merged_args[alt_key]).strip()
                break

    if "quantity" not in merged_args:
        for alt_key in ["qty", "count", "amount", "num"]:
            if alt_key in merged_args:
                try:
                    merged_args["quantity"] = float(merged_args[alt_key])
                except Exception:
                    pass
                break
    elif isinstance(merged_args.get("quantity"), str):
        try:
            merged_args["quantity"] = float(merged_args["quantity"])
        except Exception:
            merged_args["quantity"] = 1.0

    if "maxPrice" not in merged_args:
        for alt_key in ["max_price", "price", "budget", "under"]:
            if alt_key in merged_args:
                try:
                    merged_args["maxPrice"] = float(merged_args[alt_key])
                except Exception:
                    pass
                break

    try:
        res = handler(db, session_id, merged_args)
        return {"result": res, "message": res, "status": "success"}
    except ValidationError as e:
        logger.warning("Validation error on tool %s with args %s: %s", tool_name, merged_args, str(e))
        if "itemName" not in merged_args or not merged_args["itemName"]:
            return {"result": "What item would you like me to process?", "message": "What item would you like me to process?"}
        return {"result": f"Could not process item: {str(e)}", "message": f"Could not process item: {str(e)}"}
    except Exception as e:
        logger.exception("Error executing tool %s: %s", tool_name, str(e))
        return {"result": f"Execution error: {str(e)}", "message": f"Execution error: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=4444, reload=True)