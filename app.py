import base64
import io
import logging
import os
import random
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from functools import wraps

import requests
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, render_template, request, send_file, session, url_for
from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()  # reads .env locally; on Render the keys come from its environment settings

import store  # noqa: E402  (after load_dotenv, so DATABASE_URL is set)

# ---------- logging: one line per request and per image call, to stdout (Render keeps it in its Logs tab) ----------
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("storybook")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # Render's proxy terminates HTTPS
app.config.update(
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "1" if os.environ.get("RENDER") else "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)
if not os.environ.get("SECRET_KEY"):
    log.warning("SECRET_KEY is not set; sign-ins will not survive a restart")

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2.5-flare")
IMAGE_QUALITY = os.environ.get("IMAGE_QUALITY", "low")
# "openai" draws real pictures. "fake" draws small placeholder images locally after a short delay: free, for testing
# the progress bar, the database and the PDF without spending tokens.
IMAGE_PROVIDER = os.environ.get("IMAGE_PROVIDER", "openai")
PAGE_SIZE = "1024x1536"       # portrait: one book page
REFERENCE_SIZE = "1536x1024"  # landscape: Jack's and his mother's faces side by side
API_URL = "https://api.openai.com/v1/images/edits"

# The style for the whole book. Worded identically in every call; never changed mid-book.
STYLE = "Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light."

# Anything that appears on more than one page is kept consistent one of two ways:
# - Faces are too detailed to describe reliably, so Jack and his mother get a reference image (CAST below).
# - Everything simpler gets one fixed description, reused word for word on every page it appears on.
CAST = {
    "jack": "Jack (left in the reference)",
    "mother": "Jack's mother (right in the reference)",
}
RECURRING = {
    "jack": "Jack wears a patched brown wool tunic, a rope belt, green trousers, and worn leather boots.",
    "mother": "Jack's mother is a slim woman in her late thirties with the same skin tone and hair color as Jack. "
              "Her hair is tied back in a loose bun under a faded blue headscarf, and she wears a patched "
              "grey-blue dress and a cream apron.",
    "cow": "Milky-White is a gentle, thin white dairy cow with a few soft brown patches, a pink nose, "
           "short curved horns, and a frayed rope halter.",
    "cottage": "The cottage is a small one-story stone cottage with a thatched roof, a wooden front door, "
               "and one small window beside the door (one story only, no upper floor).",
    "beans": "The magic beans are five smooth beans, each a different bright color (red, orange, green, blue, "
             "and purple), each about the size of a fingernail, with a faint sparkle.",
}

REFERENCE_PROMPT = (
    'Character reference for a children\'s picture book "Jack and the Beanstalk". '
    "Draw the person in the attached photo as Jack, the hero of the story, at the same age they appear in "
    "the photo.\n"
    f"Style: {STYLE}\n"
    "Two head-and-shoulders portraits side by side on a plain light-grey background: Jack on the left, "
    "his mother on the right. Both face the viewer with a calm, neutral expression.\n"
    "Jack: keep the person's face shape, eye shape and color, skin tone, hair color and hairstyle, and any glasses "
    "or freckles, rendered in the style above, never photographic.\n"
    f"{RECURRING['mother']}\n"
    "No text, letters, or labels anywhere in the image."
)

# The storyboard. `text` is drawn onto the page by the PDF layer; the image model never sees it.
# `cast` says whose faces the page needs from the reference; `recurring` lists the fixed descriptions it uses.
# text_zone says where the art leaves room for the text; tone picks dark-on-light or light-on-dark lettering.
# Page 4 (the beanstalk at dawn) and the earlier planting/climbing scenes slot in as more entries here.
PAGES = [
    {
        "id": "cupboard",
        "title": "The empty cupboard",
        "text": "Jack and his mother had nothing left to sell but Milky-White.",
        "cast": ["jack", "mother"],
        "recurring": ["jack", "mother", "cottage", "cow"],
        "scene": "inside the cottage. Jack and his mother stand in its bare kitchen beside an empty, open "
                 "cupboard. Through the open front door, Milky-White is visible outside.\n"
                 "Jack's full face is front-lit, and he is looking at his mother.",
        "mood": "Worried and sad. Jack's mother looks tired and anxious, her shoulders slumped. Jack looks up at "
                "her with a worried face. No smiles, but gentle rather than frightening, since this is a "
                "children's book.",
        "composition": "keep the lower third of the image quiet and uncluttered (plain floorboards) "
                       "so text can sit there.",
        "text_zone": "bottom",
        "tone": "light",
    },
    {
        "id": "trade",
        "title": "The trade",
        "text": "\u201cFive magic beans,\u201d said the old man. \u201cFor one cow.\u201d",
        "cast": ["jack"],
        "recurring": ["jack", "cow", "beans"],
        "scene": "a dirt road leading to market. An old man holds out the five magic beans in his open palm. "
                 "Jack holds Milky-White by her rope halter.\n"
                 "Jack is in three-quarter view.",
        "mood": "Jack is curious and tempted, eyes wide at the beans. The old man smiles slyly, as if he knows "
                "a secret.",
        "composition": "keep the sky in the top third of the image clear and simple so text can sit there.",
        "text_zone": "top",
        "tone": "light",
    },
    {
        "id": "window",
        "title": "Out the window",
        "text": "\u201cBeans!\u201d she cried. And out the window they went.",
        "cast": ["jack", "mother"],
        "recurring": ["jack", "mother", "cottage", "beans"],
        "scene": "outside the cottage, at dusk. Jack's mother leans out of the small ground-floor window and "
                 "throws the magic beans, which scatter into the garden in front of the cottage. Jack stands in "
                 "the open front doorway, watching.\n"
                 "Use a darker dusk palette than the daytime pages: deep blues and purples, "
                 "with warm light from the window.",
        "mood": "Jack's mother is angry and frustrated. Jack looks shocked and dismayed, his mouth open. No smiles.",
        "composition": "keep the dark grass in the lower third calm and uncluttered so text can sit there.",
        "text_zone": "bottom",
        "tone": "dark",
    },
]
# Front cover (not required by the spec). The title and the child's name are drawn by the PDF layer.
COVER = {
    "id": "cover",
    "title": "Front cover",
    "cast": ["jack"],
    "recurring": ["jack", "cottage", "beans"],
    "scene": "a grassy hill in front of the cottage in golden morning light. Jack stands in the lower middle of "
             "the picture, holding one of the magic beans up in his open palm and gazing at it. Behind the "
             "cottage, a giant beanstalk curls up into the clouds.",
    "mood": "Hopeful and full of wonder. Jack smiles.",
    "composition": "keep the sky in the top third of the image clear and simple so the book title can sit there.",
    "text_zone": "top",
    "tone": "light",
}
PAGES_BY_ID = {p["id"]: p for p in [COVER, *PAGES]}


def page_prompt(page):
    faces = " and ".join(CAST[c] for c in page["cast"])
    reference = (f"The attached reference shows the faces of {faces}. Keep their faces and hair exactly as in the "
                 "reference; their expressions follow the Mood line below.")
    if page["cast"] == ["jack"]:
        reference = ("The attached reference shows Jack's face. Keep his face and hair exactly as in the "
                     "reference; his expression follows the Mood line below.")
    recurring = "\n".join(f"- {RECURRING[r]}" for r in page["recurring"])
    return (
        "Children's picture-book page illustration.\n"
        f"Style: {STYLE}\n"
        f"{reference}\n"
        f"These appear elsewhere in the book too, so draw them exactly as described:\n{recurring}\n"
        f"Scene: {page['scene']}\n"
        f"Mood: {page['mood']}\n"
        f"Composition: {page['composition']}\n"
        "Do not draw any text, letters, or signs."
    )


def reference_for(page, reference_img):
    """Attach only the faces this page needs: Jack is the left half of the reference, his mother the right."""
    if "mother" in page["cast"]:
        return reference_img
    im = Image.open(io.BytesIO(reference_img)).convert("RGB")
    out = io.BytesIO()
    im.crop((0, 0, im.width // 2, im.height)).save(out, "PNG")
    return out.getvalue()


def edit_prompt(change):
    # Same page with one thing changed: edit the existing art instead of drawing a new picture.
    return (
        "Edit this children's picture-book page. Keep everything else exactly the same: the characters, their "
        "faces and clothes, the composition, the lighting, and the empty text area.\n"
        f"Style: {STYLE}\n"
        f"Change only this: {change}\n"
        "Do not draw any text, letters, or signs."
    )


def sniff_image(data):
    """Identify the image type from its first bytes instead of trusting the browser's MIME type."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


class InputError(Exception):
    pass


def read_image(field):
    f = request.files.get(field)
    data = f.read() if f is not None else b""
    if not data:
        raise InputError("No photo was received. Choose your photo again.")
    kind = sniff_image(data)
    if kind is None:
        raise InputError("Upload a JPEG, PNG, or WebP photo (HEIC from iPhones is not supported).")
    return data, kind


def to_jpeg(png_bytes, quality=90):
    """Stored and re-sent as JPEG: about a fifth the size of the PNG the API returns."""
    out = io.BytesIO()
    Image.open(io.BytesIO(png_bytes)).convert("RGB").save(out, "JPEG", quality=quality)
    return out.getvalue()


def fake_image(slot, size):
    """Free stand-in for the image API: a small labelled placeholder, after a realistic-ish delay."""
    time.sleep(random.uniform(3, 9))
    w, h = (int(n) // 3 for n in size.split("x"))  # low-res: 512x341 or 341x512
    hue = random.randint(0, 255)
    im = Image.new("RGB", (w, h), (120 + hue // 3, 160, 220 - hue // 3))
    d = ImageDraw.Draw(im)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=(120 + hue // 3, 160 + y * 60 // h, 220 - hue // 3))
    d.ellipse((w // 2 - 40, h // 2 - 60, w // 2 + 40, h // 2 + 20), fill=(255, 224, 189), outline=(42, 36, 56), width=3)
    d.text((12, 12), f"TEST IMAGE: {slot}", fill=(42, 36, 56))
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def call_image_api(prompt, image, kind, size, slot):
    """Exactly one image API call; no retries or loops. Returns PNG bytes."""
    if IMAGE_PROVIDER == "fake":
        return fake_image(slot, size)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Server is missing OPENAI_API_KEY.")
    mimetype, ext = kind
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}"},
        data={"model": IMAGE_MODEL, "prompt": prompt, "size": size, "quality": IMAGE_QUALITY, "n": "1"},
        files={"image": (f"image.{ext}", image, mimetype)},
        timeout=170,
    )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message") or "Image API error"
        except ValueError:
            msg = "Image API error"
        if "safety system" in msg:
            msg = ("OpenAI's safety filter refused this image. Try a different photo: one person, a clear, "
                   f"well-lit face, nothing else in frame. ({msg})")
        raise RuntimeError(msg)
    return base64.b64decode(resp.json()["data"][0]["b64_json"])


def draw_slot(user_id, slot, prompt, image, kind, size=PAGE_SIZE):
    """Draw one picture and save it. Runs on a worker thread; every outcome lands in the database and the log."""
    store.set_slot(user_id, slot, state="drawing", error="", started_at=store.now())
    event = store.log_event("image", user_id, slot, detail=f"provider={IMAGE_PROVIDER} model={IMAGE_MODEL}")
    t0 = time.monotonic()
    try:
        png = call_image_api(prompt, image, kind, size, slot)
        jpeg = to_jpeg(png)
    except Exception as e:  # noqa: BLE001  any failure becomes a message on that one picture
        secs = time.monotonic() - t0
        msg = str(e) if isinstance(e, RuntimeError) else "Something went wrong drawing this picture."
        log.warning("image failed user=%s slot=%s seconds=%.1f error=%r", user_id, slot, secs, str(e)[:300])
        if not isinstance(e, RuntimeError):
            log.exception("unexpected error drawing user=%s slot=%s", user_id, slot)
        store.finish_event(event, False, secs, msg)
        store.set_slot(user_id, slot, state="error", error=msg)
        return None
    secs = time.monotonic() - t0
    log.info("image done user=%s slot=%s seconds=%.1f bytes=%d", user_id, slot, secs, len(jpeg))
    store.finish_event(event, True, secs)
    store.set_slot(user_id, slot, state="done", image=jpeg, error="")
    return jpeg


def draw_page_from_reference(user_id, page, ref_jpeg):
    data = reference_for(page, ref_jpeg)
    kind = ("image/jpeg", "jpg") if "mother" in page["cast"] else ("image/png", "png")
    return draw_slot(user_id, page["id"], page_prompt(page), data, kind)


# Pictures are drawn on background threads so a page refresh, or closing the tab, doesn't stop the book.
# The cover and the pages only need the reference, so once it exists they're all drawn at the same time.
DRAWN_IDS = [COVER["id"]] + [p["id"] for p in PAGES]
SLOT_IDS = ["ref"] + DRAWN_IDS
workers = ThreadPoolExecutor(max_workers=int(os.environ.get("IMAGE_THREADS", "8")), thread_name_prefix="draw")


def make_book_job(user_id, photo, kind):
    t0 = time.monotonic()
    ref = draw_slot(user_id, "ref", REFERENCE_PROMPT, photo, kind, size=REFERENCE_SIZE)
    if ref is None:
        for sid in DRAWN_IDS:
            store.set_slot(user_id, sid, state="error", error="The cast couldn't be drawn, so this page wasn't started.")
        return
    futures = [workers.submit(draw_page_from_reference, user_id, PAGES_BY_ID[sid], ref) for sid in DRAWN_IDS]
    ok = sum(f.result() is not None for f in futures)
    log.info("book done user=%s pages_ok=%d/%d seconds=%.1f", user_id, ok, len(DRAWN_IDS), time.monotonic() - t0)


def run_in_background(fn, *args):
    def safe():
        try:
            fn(*args)
        except Exception:  # noqa: BLE001
            log.exception("background job failed")
    threading.Thread(target=safe, daemon=True, name="book").start()


# ---------- sign-in with Google ----------

oauth = OAuth(app)
oauth.register(
    "google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
# Local testing without Google credentials: DEV_LOGIN=1 adds /login/dev, which only answers on localhost.
DEV_LOGIN = os.environ.get("DEV_LOGIN") == "1" and not os.environ.get("RENDER")


def current_user():
    if "user" not in g:
        uid, sub = session.get("uid"), session.get("sub")
        user = store.get_user(uid) if uid and sub else None
        # The cookie names both the account number and the Google account; both must match, so a cookie from a
        # wiped or replaced database can never land in someone else's account.
        g.user = user if user and user.google_sub == sub else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if current_user() is None:
            return jsonify(error="Sign in with Google first."), 401
        return view(*a, **kw)
    return wrapped


def sign_in(sub, email, name, picture):
    user = store.upsert_user(sub, email, name, picture)
    session.clear()
    session.permanent = True
    session["uid"] = user.id
    session["sub"] = user.google_sub
    store.log_event("login", user.id, detail=email)
    log.info("login user=%s", user.id)


@app.get("/login")
def login():
    if not os.environ.get("GOOGLE_CLIENT_ID"):
        return "Google sign-in isn't configured (GOOGLE_CLIENT_ID is missing).", 503
    return oauth.google.authorize_redirect(url_for("auth_callback", _external=True), prompt="select_account")


@app.get("/auth/callback")
def auth_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:  # noqa: BLE001  e.g. the user pressed Cancel, or a stale state cookie
        log.warning("login failed error=%r", str(e)[:300])
        return redirect(url_for("index", signin="failed"))
    info = token.get("userinfo") or {}
    if not info.get("email_verified", True):
        return redirect(url_for("index", signin="unverified"))
    sign_in(info["sub"], info.get("email", ""), info.get("name", ""), info.get("picture", ""))
    return redirect(url_for("index"))


@app.get("/login/dev")
def login_dev():
    if not DEV_LOGIN or request.host.split(":")[0] not in ("localhost", "127.0.0.1"):
        return "Not found", 404
    sign_in("dev-" + request.args.get("as", "tester"), "tester@localhost", "Local Tester", "")
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    log.info("logout user=%s", session.get("uid"))
    session.clear()
    return redirect(url_for("index"))


# ---------- request logging ----------

@app.before_request
def start_timer():
    g.t0 = time.monotonic()
    g.rid = uuid.uuid4().hex[:8]


@app.after_request
def log_request(resp):
    if request.path.startswith("/static/"):
        return resp
    ms = (time.monotonic() - g.get("t0", time.monotonic())) * 1000
    level = logging.DEBUG if request.path in ("/api/book", "/healthz") or request.path.startswith("/img/") else logging.INFO
    log.log(level, "rid=%s %s %s status=%s ms=%.0f user=%s ip=%s", g.get("rid"), request.method, request.path,
            resp.status_code, ms, session.get("uid"), request.headers.get("CF-Connecting-IP") or request.remote_addr)
    return resp


@app.errorhandler(Exception)
def unhandled(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    log.exception("rid=%s unhandled error on %s", g.get("rid"), request.path)
    return jsonify(error="Something went wrong on the server. Try again."), 500


# ---------- rate limit: per signed-in user, counted from the event log so it survives restarts ----------

RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "100"))


def over_limit(user_id, needed):
    used = store.images_in_last_hour(user_id)
    if used + needed <= RATE_LIMIT_PER_HOUR:
        return None
    log.info("rate limited user=%s used=%d needed=%d", user_id, used, needed)
    return jsonify(error=f"You've reached the limit of {RATE_LIMIT_PER_HOUR} pictures per hour. "
                         "Try again later."), 429


STALE_AFTER = 300  # a picture "drawing" for longer than this was cut off by a restart


def slot_view(x):
    if x is None:
        return {"state": "idle", "version": 0, "error": "", "elapsed": 0}
    state, error, elapsed = x.state, x.error, 0
    if state in ("queued", "drawing") and x.started_at:
        elapsed = (store.now() - store.aware(x.started_at)).total_seconds()
        if elapsed > STALE_AFTER:
            state, error = ("done" if x.image else "error"), "The server restarted while drawing this. Redraw it."
    return {"state": state, "version": x.version or 0, "error": error,
            "elapsed": round(elapsed, 1) if state == "drawing" else 0}


def busy(slots):
    return any(slot_view(x)["state"] in ("queued", "drawing") for x in slots.values())


# ---------- pages ----------

@app.get("/")
def index():
    user = current_user()
    return render_template("index.html", cover=COVER, pages=PAGES, user=user,
                           signin_error=request.args.get("signin"), dev_login=DEV_LOGIN)


LEGAL_EFFECTIVE = "November 19, 2026"


@app.get("/privacy")
def privacy():
    return render_template("legal.html", page="privacy", title="Privacy Policy", effective=LEGAL_EFFECTIVE,
                           contact=os.environ.get("CONTACT_EMAIL"))


@app.get("/terms")
def terms():
    return render_template("legal.html", page="terms", title="Terms of Service", effective=LEGAL_EFFECTIVE,
                           contact=os.environ.get("CONTACT_EMAIL"))


@app.post("/account/delete")
@login_required
def delete_account():
    uid = current_user().id
    _, slots = store.get_book(uid)
    if busy(slots):
        return jsonify(error="Wait for your book to finish drawing, then delete it."), 409
    store.delete_user(uid)
    session.clear()
    log.info("account deleted user=%s", uid)
    return jsonify(ok=True)


@app.get("/healthz")
def healthz():
    return f"ok {store.engine.dialect.name}"


@app.get("/api/book")
@login_required
def api_book():
    """Everything the page needs to restore the book, and the progress of anything still drawing."""
    uid = current_user().id
    book, slots = store.get_book(uid)
    fake = IMAGE_PROVIDER == "fake"
    return jsonify(
        details={"name": book.name, "age": book.age, "favorites": book.favorites},
        slots={sid: slot_view(slots.get(sid)) for sid in SLOT_IDS},
        typical={"ref": store.typical_seconds("ref", 6 if fake else 50),
                 "page": store.typical_seconds("page", 6 if fake else 45)},
    )


def clean_details(body):
    name = str(body.get("name") or "").strip()[:40]
    age = str(body.get("age") or "").strip()[:3]
    favorites = str(body.get("favorites") or "").strip()[:300]
    if age and not age.isdigit():
        raise InputError("Age should be a number.")
    return name, age, favorites


@app.post("/api/details")
@login_required
def api_details():
    try:
        store.save_details(current_user().id, *clean_details(request.get_json(silent=True) or {}))
    except InputError as e:
        return jsonify(error=str(e)), 400
    return jsonify(ok=True)


@app.get("/img/<slot>")
@login_required
def img(slot):
    data = store.slot_image(current_user().id, slot) if slot in SLOT_IDS else None
    if not data:
        return "Not found", 404
    resp = send_file(io.BytesIO(data), mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "private, max-age=31536000, immutable"  # the URL carries ?v=<version>
    return resp


@app.post("/book")
@login_required
def make_book():
    """Start a new book: the cast first, then the cover and every page at the same time. Returns at once."""
    uid = current_user().id
    try:
        photo, kind = read_image("photo")
        name, age, favorites = clean_details(request.form)
    except InputError as e:
        return jsonify(error=str(e)), 400
    if not name:
        return jsonify(error="Write the child's name on the bookplate first."), 400
    _, slots = store.get_book(uid)
    if busy(slots):
        return jsonify(error="Your book is still being drawn. Wait for it to finish."), 409
    if (resp := over_limit(uid, len(SLOT_IDS))):
        return resp
    store.save_details(uid, name, age, favorites)
    for sid in SLOT_IDS:
        store.set_slot(uid, sid, state="queued", error="", started_at=store.now())
    log.info("book started user=%s", uid)
    run_in_background(make_book_job, uid, photo, kind)
    return jsonify(ok=True), 202


@app.post("/page")
@login_required
def page():
    """Redraw one page from the saved cast reference, or edit it when `change` is given. Returns at once."""
    uid = current_user().id
    p = PAGES_BY_ID.get(request.form.get("page"))
    if p is None:
        return jsonify(error="Unknown page. Reload and try again."), 400
    change = (request.form.get("change") or "").strip()
    if len(change) > 200:
        return jsonify(error="Keep the change to 200 characters or fewer."), 400
    _, slots = store.get_book(uid)
    if slot_view(slots.get(p["id"]))["state"] in ("queued", "drawing") or slot_view(slots.get("ref"))["state"] in ("queued", "drawing"):
        return jsonify(error="That page is already being drawn."), 409
    if change:
        current = store.slot_image(uid, p["id"])
        if not current:
            return jsonify(error="Draw this page before changing it."), 400
        job = (draw_slot, uid, p["id"], edit_prompt(change), current, ("image/jpeg", "jpg"))
    else:
        ref = store.slot_image(uid, "ref")
        if not ref:
            return jsonify(error="Make the book first: the cast hasn't been drawn."), 400
        job = (draw_page_from_reference, uid, p, ref)
    if (resp := over_limit(uid, 1)):
        return resp
    store.set_slot(uid, p["id"], state="queued", error="", started_at=store.now())
    workers.submit(*job)
    return jsonify(ok=True), 202
# ---------- PDF ----------

PAGE_W, PAGE_H = 432, 648  # 6 x 9 inches, same 2:3 shape as the art


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


INK = hex_rgb("#2A2438")
PAPER = hex_rgb("#FFFBF1")
DUSK = hex_rgb("#34396B")
SOFT = hex_rgb("#5A5266")

# Andika was designed for early readers. Static TTFs, because variable fonts are unreliable in PDF libraries.
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
for _name, _file in (("Andika", "Andika-Regular.ttf"), ("Andika-Bold", "Andika-Bold.ttf"),
                     ("Andika-Italic", "Andika-Italic.ttf")):
    pdfmetrics.registerFont(TTFont(_name, os.path.join(FONT_DIR, _file)))


def draw_story_text(c, text, zone, tone):
    size, lead, pad = 21, 28, 16
    lines = simpleSplit(text, "Andika", size, PAGE_W - 2 * 36 - 2 * pad)
    box_h = len(lines) * lead + 2 * pad
    y0 = 40 if zone == "bottom" else PAGE_H - 40 - box_h
    fg, bg = (INK, PAPER) if tone == "light" else (PAPER, DUSK)
    c.saveState()
    c.setFillColorRGB(*bg)
    c.setFillAlpha(0.88)
    c.roundRect(36, y0, PAGE_W - 72, box_h, 16, stroke=0, fill=1)
    c.restoreState()
    c.setFillColorRGB(*fg)
    c.setFont("Andika", size)
    y = y0 + box_h - pad - size + 4
    for line in lines:
        c.drawCentredString(PAGE_W / 2, y, line)
        y -= lead


def jack_portrait(reference_img):
    """Jack is the left half of the face reference; crop him out for the About Me page."""
    im = Image.open(io.BytesIO(reference_img)).convert("RGB")
    w, h = im.size
    half = im.crop((0, 0, w // 2, h))
    target_w = half.height * 2 // 3  # 2:3 portrait, centered on Jack
    left = max(0, (half.width - target_w) // 2)
    return half.crop((left, 0, left + min(target_w, half.width), half.height))


def draw_cover(c, img, name):
    """Full-bleed art with a dusk title band across the top, matching the web preview."""
    c.drawImage(ImageReader(io.BytesIO(img)), 0, 0, PAGE_W, PAGE_H)
    title_lines = simpleSplit("Jack and the Beanstalk", "Andika-Bold", 38, PAGE_W - 80)
    box_h = 24 + len(title_lines) * 42 + 30 + 18
    y0 = PAGE_H - 40 - box_h
    c.saveState()
    c.setFillColorRGB(*DUSK)
    c.setFillAlpha(0.92)
    c.rect(0, y0, PAGE_W, box_h, stroke=0, fill=1)
    c.restoreState()
    c.setFillColorRGB(*hex_rgb("#F2C96A"))  # gold foil, matching the web cover
    y = y0 + box_h - 24 - 30
    c.setFont("Andika-Bold", 38)
    for line in title_lines:
        c.drawCentredString(PAGE_W / 2, y, line)
        y -= 42
    c.setFont("Andika-Italic", 21)
    c.drawCentredString(PAGE_W / 2, y + 8, f"starring {name}")


def build_pdf(cover_img, images, reference_img, name, age, favorites):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Jack and the Beanstalk, starring {name}")
    draw_cover(c, cover_img, name)
    c.showPage()
    for p, img in zip(PAGES, images):
        c.drawImage(ImageReader(io.BytesIO(img)), 0, 0, PAGE_W, PAGE_H)  # full bleed
        draw_story_text(c, p["text"], p["text_zone"], p["tone"])
        c.showPage()

    # Last page: About Me
    c.setFillColorRGB(*PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColorRGB(*INK)
    c.setFont("Andika-Bold", 34)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 72, "About Me")
    if reference_img:
        c.drawImage(ImageReader(jack_portrait(reference_img)), PAGE_W / 2 - 100, PAGE_H - 400, 200, 300)
    y = PAGE_H - 445
    c.setFont("Andika-Bold", 26)
    c.drawCentredString(PAGE_W / 2, y, name)
    y -= 34
    c.setFont("Andika", 17)
    if age:
        c.drawCentredString(PAGE_W / 2, y, f"Age {age}")
        y -= 30
    if favorites:
        c.setFillColorRGB(*SOFT)
        c.setFont("Andika-Italic", 15)
        c.drawCentredString(PAGE_W / 2, y, "My favorite things")
        y -= 22
        c.setFillColorRGB(*INK)
        c.setFont("Andika", 15)
        for line in simpleSplit(favorites, "Andika", 15, PAGE_W - 96)[:6]:
            c.drawCentredString(PAGE_W / 2, y, line)
            y -= 21
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


@app.get("/book.pdf")
@login_required
def pdf():
    """Bind the saved book into a PDF: cover, pages, About Me."""
    uid = current_user().id
    book, slots = store.get_book(uid)
    if not book.name:
        return jsonify(error="Write the child's name on the bookplate for the About Me page."), 400
    images = {sid: slots[sid].image if sid in slots else None for sid in SLOT_IDS}
    missing = [sid for sid in DRAWN_IDS if not images[sid]]
    if missing:
        return jsonify(error="Draw every page before downloading."), 400
    t0 = time.monotonic()
    buf = build_pdf(images["cover"], [images[p["id"]] for p in PAGES], images["ref"], book.name, book.age,
                    book.favorites)
    store.log_event("pdf", uid, ok=True, seconds=time.monotonic() - t0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="JackAndTheBeanstalk.pdf")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
