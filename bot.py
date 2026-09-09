# -*- coding: utf-8 -*-
"""Talkin Chat launcher for the legacy command/game bot.

The original Giant implementation is kept in bot_giant_backup.py. This
launcher routes Talkin room text into its command handler and routes replies
and media back through the Talkin WebSocket.
"""
import asyncio
import logging
import os

import aiohttp

os.environ.setdefault("TALKIN_MODE", "1")
from talkin_protocol import BOT_ID as TALKIN_BOT_ID, BOT_MASTER, GROUP_TO_JOIN
from talkin_transport import TalkinTransport
import bot_giant_backup as legacy

log = logging.getLogger("talkin-wrapper")
transport = None

async def on_talkin_message(room, text, sender, media_url=None, message_type=None):
    legacy.rooms.setdefault(room, room)
    legacy.last_room[room] = legacy.now_iso()
    if sender == TALKIN_BOT_ID:
        return
    try:
        reply = await legacy.handle_room(room, text or "", sender, media_url, message_type)
        if reply:
            await room_send(room, reply)
    except Exception:
        log.exception("legacy command handler failed")
        if transport:
            transport.send_private_text(BOT_MASTER, "❌ حدث خطأ أثناء تنفيذ الأمر في غرفة " + str(room))

async def room_send(room, text):
    if transport:
        value = str(text)
        if value.startswith(("❌", "⚠️")) or "تعذر" in value or "فشل" in value:
            transport.send_private_text(BOT_MASTER, f"{value}\n📍 الغرفة: {room}")
        else:
            transport.send_room_text(room, value)

async def room_send_media(room, text, media_url, m_type="image", duration_ms=None):
    if transport and media_url:
        transport.send_room_media(room, media_url, m_type, text or "", duration_ms)

async def dm_send_bridge(username, text):
    if transport and username:
        transport.send_private_text(str(username), str(text))

async def dm_send_media_bridge(username, text, media_url, m_type="image"):
    if transport and username:
        transport.send_private_text(str(username), str(text or media_url))

async def main():
    global transport
    legacy.room_send = room_send
    legacy.room_send_media = room_send_media
    legacy.dm_send = dm_send_bridge
    legacy.dm_send_media = dm_send_media_bridge
    legacy.BOT_ID = TALKIN_BOT_ID
    if GROUP_TO_JOIN:
        legacy.rooms[GROUP_TO_JOIN] = GROUP_TO_JOIN
        legacy.last_room[GROUP_TO_JOIN] = legacy.now_iso()
    # Serve generated gifts/audio through the single Railway public URL.
    try:
        await legacy.start_media_server()
    except Exception:
        log.exception("media server startup failed")
    legacy.http = aiohttp.ClientSession()
    loop = asyncio.get_running_loop()
    transport = TalkinTransport(loop, on_talkin_message)
    transport.start()
    log.info("Talkin launcher started; room=%s", GROUP_TO_JOIN or "not configured")
    try:
        await asyncio.Event().wait()
    finally:
        try:
            await legacy.http.close()
        except Exception:
            pass
        try:
            await legacy.stop_media_server()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
