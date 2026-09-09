import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
_started = None


def start_media_server():
    global _started
    if _started:
        return _started
    port = int(os.getenv("PORT", "8080"))
    root = BASE_DIR

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)
        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    thread = threading.Thread(target=server.serve_forever, name="media-http", daemon=True)
    thread.start()
    _started = server
    return server


def public_url(relative_path):
    base = (os.getenv("PUBLIC_BASE_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip().rstrip("/")
    if not base:
        return ""
    if not base.startswith("http://") and not base.startswith("https://"):
        base = "https://" + base
    return base + "/" + str(relative_path).lstrip("/")
