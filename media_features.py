import base64
import json
import os
import random
import time
import uuid
from pathlib import Path

try:
    import yt_dlp
except Exception:
    yt_dlp = None
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = ImageDraw = ImageFont = None
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception:
    arabic_reshaper = None
    get_display = None

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "media_state.json"

GIFTS = [
    ("1", "وردة", "🌹", 10), ("2", "قلب", "❤️", 20),
    ("3", "قبلة", "💋", 30), ("4", "هدية", "🎁", 50),
    ("5", "تاج", "👑", 100), ("6", "ألعاب نارية", "🎆", 150),
]

GIFT_IMAGES = {
    "1": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f337.png",
    "2": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/2764.png",
    "3": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f48b.png",
    "4": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f381.png",
    "5": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f451.png",
    "6": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f386.png",
}

GIFT_TEMPLATES = {
    "1": "gift_template_rose.webp", "2": "gift_template_heart.webp",
    "3": "gift_template_kiss.webp", "4": "gift_template_present.webp",
    "5": "gift_template_crown.webp", "6": "gift_template_heart.webp",
}

HELP = (
    "🎵 الأغاني: اكتب: اغنية اسم الأغنية أو موسيقى اسم الأغنية\n"
    "🎮 الألعاب: ألعاب | نرد | حجر ورق مقص | تخمين 1-10\n"
    "🎁 الهدايا: هدايا | هدية@رقم@اسم المستخدم\n"
    "ℹ️ يتم إرسال رابط الأغنية من مصدرها، ولا يتم حفظ كلمات المرور أو Cookies في الكود."
)


def _load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"scores": {}, "last_music": {}}


def _save_state(data):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _normalize_cookie_text(raw):
    text = str(raw or "")
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")
    text = text.replace("\\t", "\t").replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            lines.append(line)
            continue
        fields = line.split("\t")
        if len(fields) < 7:
            fields = line.split()
        if len(fields) >= 7:
            lines.append("\t".join(fields[:7]))
    if not any(line.startswith("# Netscape HTTP Cookie File") for line in lines):
        lines.insert(0, "# Netscape HTTP Cookie File")
    return "\n".join(lines) + "\n"


def _youtube_cookie_files():
    paths = []
    names = ["YOUTUBE_COOKIES"] + [f"YOUTUBE_COOKIES_{i}" for i in range(1, 11)]
    for index, name in enumerate(names):
        raw = os.getenv(name, "").strip()
        if not raw:
            continue
        if raw.startswith("base64:"):
            try:
                raw = base64.b64decode(raw[7:]).decode("utf-8", "replace")
            except Exception:
                continue
        path = Path(f"/tmp/youtube_cookies_{index}.txt")
        content = _normalize_cookie_text(raw)
        if len([x for x in content.splitlines() if x and not x.startswith("#")]) > 0:
            path.write_text(content, encoding="utf-8")
            paths.append(str(path))
    configured = os.getenv("YOUTUBE_COOKIES_PATH", "").strip()
    if configured and Path(configured).is_file():
        paths.append(configured)
    return paths


def _youtube_options(cookie_file=None):
    options = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "noplaylist": True, "format": "bestaudio/best",
        "socket_timeout": 35, "retries": 3,
        "http_headers": {"User-Agent": "Mozilla/5.0 Chrome/131.0 Safari/537.36"},
    }
    clients = os.getenv("YOUTUBE_PLAYER_CLIENTS", "default,web_embedded").strip()
    options["extractor_args"] = {"youtube": {"player_client": [x.strip() for x in clients.split(",") if x.strip()] or ["default"]}}
    po_token = os.getenv("YOUTUBE_PO_TOKEN", "").strip()
    if po_token:
        options["extractor_args"]["youtube"]["po_token"] = po_token
    if cookie_file:
        options["cookiefile"] = cookie_file
    return options


def _shape_arabic(text):
    text = str(text or "")
    if arabic_reshaper and get_display:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            pass
    return text


def render_gift(gift_id, sender, receiver):
    if not Image or not ImageFont:
        return None
    assets = BASE_DIR / "assets"
    template_path = assets / GIFT_TEMPLATES.get(str(gift_id), "gift_template_present.webp")
    if not template_path.is_file():
        return None
    template = Image.open(template_path).convert("RGBA")
    width, height = template.size
    colors_bg = [(20, 25, 55), (50, 18, 70), (16, 62, 70), (80, 32, 35)]
    bg = Image.new("RGBA", (width, height), random.choice(colors_bg) + (255,))
    draw_bg = ImageDraw.Draw(bg)
    for _ in range(8):
        x, y = random.randrange(width), random.randrange(height)
        r = random.randrange(25, max(26, min(width, height) // 3))
        draw_bg.ellipse((x-r, y-r, x+r, y+r), fill=(255, 255, 255, random.randrange(8, 30)))
    image = Image.alpha_composite(bg, template)
    draw = ImageDraw.Draw(image)
    font_path = assets / "Amiri-Bold.ttf"
    if not font_path.is_file():
        font_path = assets / "NotoSansArabic-SemiBold.ttf"
    font = ImageFont.truetype(str(font_path), max(24, int(height * 0.07)))
    box_left, box_right = int(width * 0.12), int(width * 0.88)
    from_y, to_y = int(height * 0.78), int(height * 0.88)
    box_h = max(48, int(height * 0.08))
    colors = [(255, 92, 155), (80, 220, 255), (255, 211, 72), (157, 116, 255), (80, 235, 150)]
    for name, y, color in ((_shape_arabic("@" + sender), from_y, random.choice(colors)),
                           (_shape_arabic("@" + receiver), to_y, random.choice(colors))):
        while draw.textbbox((0, 0), name, font=font)[2] > box_right - box_left - 24 and font.size > 14:
            font = ImageFont.truetype(str(font_path), font.size - 2)
        bbox = draw.textbbox((0, 0), name, font=font, stroke_width=1)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.rounded_rectangle((box_left, y - 8, box_right, y + box_h), radius=18,
                               fill=(5, 13, 31, 220), outline=(230, 177, 65, 230), width=3)
        draw.text((x + 2, y + 2), name, font=font, fill=(0, 0, 0), stroke_width=3, stroke_fill=(0, 0, 0))
        draw.text((x, y), name, font=font, fill=color, stroke_width=1, stroke_fill=(255, 255, 255))
    out_dir = BASE_DIR / "generated_gifts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"gift_{gift_id}_{uuid.uuid4().hex}.png"
    image.save(out, "PNG", optimize=True)
    return out


def _music_result(query):
    if not yt_dlp:
        return None, "مكتبة البحث عن الأغاني غير مثبتة على Railway."
    last_error = None
    cookie_files = _youtube_cookie_files() or [None]
    for cookie_file in cookie_files:
        try:
            with yt_dlp.YoutubeDL(_youtube_options(cookie_file)) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            entry = (info.get("entries") or [None])[0]
            if not entry:
                return None, "لم أجد نتيجة للأغنية."
            url = entry.get("url") or entry.get("webpage_url") or entry.get("original_url")
            return {"title": entry.get("title") or query, "url": url,
                    "duration_ms": int(float(entry.get("duration") or 0) * 1000)}, None
        except Exception as exc:
            last_error = exc
    return None, f"تعذر البحث عن الأغنية: {type(last_error).__name__ if last_error else 'UnknownError'}"


def handle(bot, room, sender, text):
    """Handle transferred music/game/gift commands.

    Returns True when the command belongs to this feature layer. The bot
    argument must expose send_room_text(room, text).
    """
    raw = (text or "").strip()
    low = raw.casefold()
    if low in ("مساعدة الوسائط", "مساعدة الاغاني", "مساعدة الأغاني", "media help"):
        bot.send_room_text(room, HELP)
        return True

    if low in ("هدايا", "الهدايا", "gift", "gifts"):
        lines = ["🎁 كتالوج الهدايا", "━━━━━━━━━━━━"]
        lines += [f"{i} - {name} {emoji} | {cost} نقطة" for i, name, emoji, cost in GIFTS]
        lines.append("للإرسال: هدية@رقم@اسم المستخدم")
        bot.send_room_text(room, "\n".join(lines))
        return True

    if low.startswith(("هدية@", "هديه@", "gift@")):
        parts = raw.split("@")
        if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
            bot.send_room_text(room, "❌ الصيغة الصحيحة: هدية@رقم@اسم المستخدم")
            return True
        gift = next((g for g in GIFTS if g[0] == parts[1].strip()), None)
        if not gift:
            bot.send_room_text(room, "❌ رقم الهدية غير موجود. اكتب: هدايا")
            return True
        _, name, emoji, cost = gift
        receiver = parts[2].strip()
        caption = f"{emoji} 🎁 @{sender} أرسل {name} إلى @{receiver} | القيمة: {cost} نقطة"
        image_url = ""
        try:
            rendered = render_gift(gift[0], sender, receiver)
            if rendered:
                from media_server import public_url
                image_url = public_url(f"generated_gifts/{rendered.name}")
        except Exception:
            image_url = ""
        image_url = image_url or GIFT_IMAGES.get(gift[0])
        if hasattr(bot, "send_room_media") and image_url:
            bot.send_room_media(room, caption, image_url, media_type="image")
        else:
            bot.send_room_text(room, caption)
        return True

    if low in ("ألعاب", "العاب", "games", "game"):
        bot.send_room_text(room, "🎮 الألعاب المتاحة: نرد | حجر ورق مقص | تخمين 1-10")
        return True
    if low in ("نرد", "dice", "رمي النرد"):
        bot.send_room_text(room, f"🎲 @{sender} رمى النرد وظهر الرقم: {random.randint(1, 6)}")
        return True
    if low in ("حجر", "ورق", "مقص") or low.startswith(("حجر ورق مقص ", "rps ")):
        choices = ["حجر", "ورق", "مقص"]
        user = raw.split()[-1] if len(raw.split()) > 2 else raw
        user = {"rock": "حجر", "paper": "ورق", "scissors": "مقص"}.get(user.casefold(), user)
        if user not in choices:
            bot.send_room_text(room, "اكتب: حجر أو ورق أو مقص")
            return True
        computer = random.choice(choices)
        win = (user, computer) in (("حجر", "مقص"), ("ورق", "حجر"), ("مقص", "ورق"))
        result = "تعادل" if user == computer else ("فاز" if win else "خسر")
        bot.send_room_text(room, f"🎮 @{sender}: {user} | البوت: {computer} | النتيجة: {result}")
        return True
    if low.startswith(("تخمين", "guess")):
        try:
            guess = int(raw.split()[-1])
            if not 1 <= guess <= 10:
                raise ValueError
        except ValueError:
            bot.send_room_text(room, "اكتب رقماً من 1 إلى 10، مثال: تخمين 7")
            return True
        answer = random.randint(1, 10)
        bot.send_room_text(room, f"🔢 @{sender} اختار {guess}. الرقم كان {answer} — " + ("أحسنت! 🎉" if guess == answer else "حظاً أوفر!"))
        return True

    if low.startswith(("اغنية ", "أغنية ", "موسيقى ", "music ", "song ")):
        query = raw.split(" ", 1)[1].strip() if " " in raw else ""
        if not query:
            bot.send_room_text(room, "اكتب اسم الأغنية بعد الأمر.")
            return True
        last = _load_state()
        cooldown = int(os.getenv("MUSIC_COOLDOWN_SECONDS", "20"))
        now = time.time()
        if now - float(last.get("last_music", {}).get(room, 0)) < cooldown:
            bot.send_room_text(room, f"⏳ انتظر {cooldown} ثانية قبل طلب أغنية أخرى.")
            return True
        last.setdefault("last_music", {})[room] = now
        _save_state(last)
        result, err = _music_result(query)
        if err:
            bot.send_room_text(room, "❌ " + err)
        else:
            caption = f"🎵 {result['title']}\n👤 طلبها: @{sender}"
            if hasattr(bot, "send_room_media") and result.get("url"):
                bot.send_room_media(room, caption, result["url"], media_type="voice",
                                    duration_ms=result.get("duration_ms", 0))
            else:
                bot.send_room_text(room, f"{caption}\n▶️ تشغيل الرابط: {result['url']}")
        return True
    return False
