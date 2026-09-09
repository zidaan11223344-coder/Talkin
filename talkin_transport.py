# -*- coding: utf-8 -*-
"""Talkin Chat transport bridge.

This module wraps the protobuf/WebSocket implementation copied from the
reference Talkin bot. It deliberately keeps credentials in environment
variables and exposes a small callback-based interface to the legacy bot.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Awaitable, Callable, Optional

from talkin_protocol import BOT_ID, TalkinBot

MessageCallback = Callable[[str, str, str, Optional[str], Optional[str]], Awaitable[None]]


class TalkinTransport:
    """Run the Talkin protocol in a worker thread and bridge room messages.

    callback(room, text, sender, media_url, message_type) is invoked on the
    asyncio loop supplied to ``start``. The protocol's native send methods are
    exposed for the application layer.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, callback: MessageCallback):
        self.loop = loop
        self.callback = callback
        self.bot = TalkinBot()
        self.thread: Optional[threading.Thread] = None
        self._original_handler = self.bot.handle_room_event

        def handler(result):
            self._original_handler(result)
            self._bridge_event(result)

        self.bot.handle_room_event = handler

    def _bridge_event(self, result):
        event = result.get("room_event") if isinstance(result, dict) else None
        if not isinstance(event, dict):
            return
        # Talkin protocol fields are decoded as numeric keys by the supplied
        # implementation: 1=event type, 3=sender, 5=body, 6=room.
        event_type = str(event.get(1, "") or "")
        if event_type not in ("text", "message", "room_message"):
            return
        room = str(event.get(6, "") or "").strip()
        sender = str(event.get(3, "") or "").strip()
        text = str(event.get(5, "") or "")
        if not room or not text or not sender or sender == BOT_ID:
            return
        asyncio.run_coroutine_threadsafe(
            self.callback(room, text, sender, None, "text"), self.loop
        )

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.bot.start, name="talkin-ws", daemon=True)
        self.thread.start()

    def stop(self):
        self.bot.stop_event.set()
        try:
            if self.bot.ws:
                self.bot.ws.close()
        except Exception:
            pass

    def send_room_text(self, room: str, text: str):
        return self.bot.send_room_text(room, text)

    def send_room_media(self, room: str, media_url: str, media_type: str = "image",
                        caption: str = "", duration_ms: int = None):
        return self.bot.send_room_media(room, media_url, media_type, caption, duration_ms)

    def send_private_text(self, username: str, text: str):
        return self.bot.send_private_text(username, text)

    def join_room(self, room: str):
        self.bot.known_rooms.add(room)
        return self.bot.join_room(room)

    def send_admin(self, room: str, target: str, operation: str):
        return self.bot.send_admin(room, target, operation)

    @property
    def known_rooms(self):
        return self.bot.known_rooms

    @property
    def room_users(self):
        return self.bot.room_users
