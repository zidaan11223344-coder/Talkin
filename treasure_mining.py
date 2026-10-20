"""Local treasure-mining module required by bot.py.

Keep this file in the same directory as bot.py when deploying.
State is stored through the load/save callbacks supplied by bot.py.
"""
from __future__ import annotations

import random
import re
import time
import uuid
from pathlib import Path

# Catalog keys are stable IDs; images should exist under assets/treasures/.
ITEMS = {
    "rare_diamond": {"name": "الألماسة النادرة", "icon": "💎", "price": 500_000_000, "image": "rare_diamond.jpg", "weight": 1},
    "diamond": {"name": "ألماسة", "icon": "💎", "price": 100_000, "image": "diamond.jpg", "weight": 8},
    "ruby": {"name": "ياقوت", "icon": "🔴", "price": 50_000, "image": "ruby.jpg", "weight": 12},
    "emerald": {"name": "زمرد", "icon": "🟢", "price": 35_000, "image": "emerald.jpg", "weight": 16},
    "sapphire": {"name": "ياقوت أزرق", "icon": "🔷", "price": 25_000, "image": "sapphire.jpg", "weight": 20},
    "gold": {"name": "ذهب", "icon": "🪙", "price": 10_000, "image": "gold.jpg", "weight": 24},
    "silver": {"name": "فضة", "icon": "🥈", "price": 3_000, "image": "silver.jpg", "weight": 30},
}
DIAMOND_KEYS = ("rare_diamond", "diamond")


def _normalize(value):
    value = str(value or "").strip().casefold()
    return value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


def resolve_item_keys(selection):
    """Resolve an item name or key to a list of catalog keys."""
    text = _normalize(selection)
    if not text:
        return []
    aliases = {
        "red": "rare_diamond", "الماسه النادره": "rare_diamond",
        "الالماسه النادره": "rare_diamond", "الماس النادر": "rare_diamond",
        "الماسة النادرة": "rare_diamond", "الماسه": "diamond", "الماس": "diamond",
        "diamond": "diamond", "rare diamond": "rare_diamond",
        "ruby": "ruby", "ياقوت": "ruby", "emerald": "emerald", "زمرد": "emerald",
        "sapphire": "sapphire", "ياقوت ازرق": "sapphire", "gold": "gold", "ذهب": "gold",
        "silver": "silver", "فضه": "silver",
    }
    key = aliases.get(text, text)
    if key in ITEMS:
        return [key]
    for item_key, item in ITEMS.items():
        if text == _normalize(item.get("name")):
            return [item_key]
    return []


def format_cooldown(seconds):
    seconds = max(0, int(seconds or 0))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes} دقيقة و{secs} ثانية" if minutes else f"{secs} ثانية"


class MiningStore:
    """JSON-backed inventory and redemption store compatible with bot.py."""
    def __init__(self, path, load_json, save_json):
        self.path = Path(path)
        self._load_json = load_json
        self._save_json = save_json
        import threading
        self._lock = threading.RLock()

    def _state(self):
        state = self._load_json(self.path, {})
        if not isinstance(state, dict):
            state = {}
        state.setdefault("users", {})
        state.setdefault("pending_redemptions", {})
        return state

    def _save(self, state):
        self._save_json(self.path, state)

    @staticmethod
    def _user(state, user_id, username=""):
        users = state.setdefault("users", {})
        key = str(user_id or "").strip()
        if not key:
            key = "name:" + _normalize(username)
        user = users.setdefault(key, {"username": str(username or key), "inventory": {}, "diamonds_found": 0, "last_dig": 0})
        if username:
            user["username"] = str(username)
        user.setdefault("inventory", {})
        user.setdefault("diamonds_found", 0)
        user.setdefault("last_dig", 0)
        return key, user

    def pending_redemption(self, user_id):
        with self._lock:
            state = self._state()
            key = str(user_id or "")
            pending = state["pending_redemptions"].get(key)
            return dict(pending) if isinstance(pending, dict) else None

    def complete_redemption(self, user_id, redemption_id):
        with self._lock:
            state = self._state()
            key = str(user_id or "")
            pending = state["pending_redemptions"].get(key)
            if not isinstance(pending, dict) or str(pending.get("id")) != str(redemption_id):
                return False
            state["pending_redemptions"].pop(key, None)
            self._save(state)
            return True

    def inventory(self, user_id, username=""):
        with self._lock:
            state = self._state()
            _, user = self._user(state, user_id, username)
            self._save(state)
            return {"inventory": dict(user["inventory"]), "diamonds_found": int(user["diamonds_found"]), "username": user["username"]}

    def leaderboard(self, limit=10):
        with self._lock:
            state = self._state()
            rows = []
            for user in state.get("users", {}).values():
                if isinstance(user, dict):
                    rows.append({"username": str(user.get("username", "Unknown")), "diamonds_found": int(user.get("diamonds_found", 0) or 0)})
            rows.sort(key=lambda row: row["diamonds_found"], reverse=True)
            return rows[:max(0, int(limit))]

    def dig(self, user_id, username=""):
        with self._lock:
            state = self._state()
            key, user = self._user(state, user_id, username)
            if key in state["pending_redemptions"]:
                return {"ok": False, "error": "pending_redemption"}
            now = time.time()
            remaining = 60 - (now - float(user.get("last_dig", 0) or 0))
            if remaining > 0:
                return {"ok": False, "error": "cooldown", "remaining": int(remaining) + 1}
            user["last_dig"] = now
            pool = [(key, max(1, int(item.get("weight", 1)))) for key, item in ITEMS.items()]
            chosen = random.choices([p[0] for p in pool], weights=[p[1] for p in pool], k=1)[0]
            user["inventory"][chosen] = int(user["inventory"].get(chosen, 0) or 0) + 1
            user["diamonds_found"] = int(user.get("diamonds_found", 0) or 0) + 1
            self._save(state)
            item = dict(ITEMS[chosen])
            item["key"] = chosen
            return {"ok": True, "item": item}

    def give_test_diamond(self, user_id, username=""):
        with self._lock:
            state = self._state()
            key, user = self._user(state, user_id, username)
            rare_key = "rare_diamond"
            user["inventory"][rare_key] = int(user["inventory"].get(rare_key, 0) or 0) + 1
            user["diamonds_found"] = int(user.get("diamonds_found", 0) or 0) + 1
            self._save(state)
            return {"ok": True, "item": dict(ITEMS[rare_key])}

    def reserve_redemption(self, user_id, username, item_keys, quantity=None):
        with self._lock:
            state = self._state()
            user_key, user = self._user(state, user_id, username)
            if user_key in state["pending_redemptions"]:
                return {"ok": False, "error": "pending_redemption"}
            keys = list(item_keys or [])
            if not keys or any(key not in ITEMS for key in keys):
                return {"ok": False, "error": "invalid_item"}
            key = keys[0]
            available = int(user["inventory"].get(key, 0) or 0)
            if quantity is None:
                quantity = 1
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid_quantity"}
            if quantity <= 0:
                return {"ok": False, "error": "invalid_quantity"}
            if available <= 0:
                return {"ok": False, "error": "empty_inventory"}
            if available < quantity:
                return {"ok": False, "error": "insufficient_items", "available": available}
            user["inventory"][key] = available - quantity
            points = int(ITEMS[key]["price"]) * quantity
            pending = {"id": uuid.uuid4().hex, "items": {key: quantity}, "points": points, "created_at": time.time()}
            state["pending_redemptions"][user_key] = pending
            self._save(state)
            return {"ok": True, "pending": dict(pending)}
