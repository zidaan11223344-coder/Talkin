#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manual Talkin media smoke test.

Examples:
  python talkin_media_test.py --type image --url https://example.com/gift.png --caption '🎁 هدية'
  python talkin_media_test.py --type voice --url https://example.com/song.ogg --caption '🎵 أغنية'

The tool never prints BOT_PWD. Edit talkin_settings.py; a .env file is
optional and can override the settings.
"""
import argparse
import os
import time

from talkin_protocol import TalkinBot


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--type", choices=("image", "voice"), required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--caption", default="")
    p.add_argument("--duration-ms", type=int, default=0)
    p.add_argument("--wait", type=float, default=4.0)
    args = p.parse_args()
    if not os.getenv("BOT_ID") or not os.getenv("BOT_PWD") or not os.getenv("GROUP_TO_JOIN"):
        raise SystemExit("Edit BOT_ID, BOT_PWD and GROUP_TO_JOIN in talkin_settings.py first")
    bot = TalkinBot()
    bot.start_thread = None
    import threading
    worker = threading.Thread(target=bot.start, daemon=True)
    worker.start()
    time.sleep(max(1.0, args.wait))
    room = os.getenv("GROUP_TO_JOIN", "").strip()
    bot.send_room_media(room, args.url, args.type, args.caption, args.duration_ms or None)
    print("Media query sent to Talkin room:", room)
    time.sleep(1.0)
    bot.stop_event.set()
    try:
        bot.ws.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
