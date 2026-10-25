import base64
import io
import os
import threading
import time
from collections import defaultdict, deque

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

load_dotenv()  # reads .env locally; on Render the key comes from its environment settings

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # room for 4 page images when building the PDF

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2.5-flare")
IMAGE_QUALITY = os.environ.get("IMAGE_QUALITY", "low")
PAGE_SIZE = "1024x1536"       # portrait: one book page
REFERENCE_SIZE = "1536x1024"  # landscape: Jack and his mother side by side
API_URL = "https://api.openai.com/v1/images/edits"

# The style for the whole book. Worded identically in every call; never changed mid-book.
STYLE = "Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light."

# Fixed descriptions reused word for word, so the cast and the cottage look the same on every page.
JACK_OUTFIT = "patched brown wool tunic, rope belt, green trousers, worn leather boots"
MOTHER = ("Jack's mother: a slim woman in her late thirties with the same skin tone and hair color as Jack, "
          "her hair tied back in a loose bun under a faded blue headscarf, wearing a patched grey-blue dress "
          "and a cream apron")
COTTAGE = ("a small one-story stone cottage with a thatched roof, a wooden front door, and one small window "
           "beside the door (one story only, no upper floor)")

REFERENCE_PROMPT = (
    'Character reference sheet for a children\'s picture book "Jack and the Beanstalk". '
    "Turn the child in the attached photo into Jack.\n"
    f"Style: {STYLE}\n"
    "Two full-body characters side by side, standing, facing the viewer, arms relaxed, on a plain light-grey "
    "background: Jack on the left, his mother on the right.\n"
    "Jack: keep the child's face shape, eye shape and color, skin tone, hair color and hairstyle, and any glasses "
    f"or freckles, rendered in the style above, never photographic. Outfit: {JACK_OUTFIT}.\n"
    f"{MOTHER}.\n"
    "No text, letters, or labels anywhere in the image."
)

# The storyboard. `text` is drawn onto the page by the PDF layer; the image model never sees it.
# text_zone says where the art leaves room for it; tone picks dark-on-light or light-on-dark lettering.
# Page 4 (the beanstalk at dawn) and the earlier planting/climbing scenes slot in as more entries here.
PAGES = [
    {
        "id": "cupboard",
        "title": "The empty cupboard",
        "text": "Jack and his mother had nothing left to sell but Milky-White.",
        "scene": f"inside {COTTAGE}. Jack and his mother stand in its bare kitchen beside an empty, open "
                 "cupboard. Through the open front door, Milky-White the cow is visible outside.\n"
                 "Jack's full face is front-lit, and he is looking at his mother.",
        "composition": "keep the lower third of the image quiet and uncluttered (plain floorboards) "
                       "so text can sit there.",
        "mood": "Worried and sad. Jack's mother looks tired and anxious, her shoulders slumped. Jack looks up at her with a worried face. No smiles, but gentle rather than frightening, since this is a children's book.",
        "text_zone": "bottom",
        "tone": "light",
    },
    {
        "id": "trade",
        "title": "The trade",
        "text": "“Five magic beans,” said the old man. “For one cow.”",
        "scene": "a dirt road leading to market. An old man holds out five coloured beans in his open palm. "
                 "Jack holds Milky-White the cow by a rope.\n"
                 "Jack is in three-quarter view, wearing the same clothes as in the reference.",
        "composition": "keep the sky in the top third of the image clear and simple so text can sit there.",
        "mood": "Jack is curious and tempted, eyes wide at the beans. The old man smiles slyly, as if he knows a secret.",
        "text_zone": "top",
        "tone": "light",
    },
    {
        "id": "window",
        "title": "Out the window",
        "text": "“Beans!” she cried. And out the window they went.",
        "scene": f"outside {COTTAGE}, at dusk. Jack's mother leans out of the small ground-floor window and "
                 "throws the beans, which scatter into the garden in front of the cottage. Jack stands in the "
                 "open front doorway, watching.\n"
                 "Use a darker dusk palette than the daytime pages: deep blues and purples, "
                 "with warm light from the window.",
        "composition": "keep the dark grass in the lower third calm and uncluttered so text can sit there.",
        "mood": "Jack's mother is angry and frustrated. Jack looks shocked and dismayed, his mouth open. No smiles.",
        "text_zone": "bottom",
        "tone": "dark",
    },
]
PAGES_BY_ID = {p["id"]: p for p in PAGES}


def page_prompt(page):
    return (
        "Children's picture-book page illustration.\n"
        f"Style: {STYLE}\n"
        "The attached reference shows Jack (left) and his mother (right). Whenever they appear, keep their faces, "
        "hair, and clothes exactly as in the reference.\n"
        f"Scene: {page['scene']}\n"
        f"Mood: {page['mood']}\n"
        f"Composition: {page['composition']}\n"
        "Do not draw any text, letters, or signs."
    )


def edit_prompt(change):
    # Same page with one thing changed: edit the existing art instead of drawing a new picture.
    return (
        "Edit this children's picture-book page. Keep everything else exactly the same: the characters, their "
        "faces and clothes, the composition, the lighting, and the empty text area.\n"
        f"Style: {STYLE}\n"
        f"Change only this: {change}\n"
        "Do not draw any text, letters, or signs."
    )


# Per-visitor limit on images (a book is 4: the reference plus 3 pages). In memory, so it resets on restart.
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "12"))
_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def client_ip():
    # Render sits behind Cloudflare, which sets CF-Connecting-IP and overwrites any value the client sends.
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "unknown"


def seconds_until_allowed(ip):
    """Record a hit for this IP and return 0, or return how long to wait if the hourly limit is used up."""
    now = time.monotonic()
    with _hits_lock:
        hits = _hits[ip]
        while hits and now - hits[0] >= 3600:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_PER_HOUR:
            return 3600 - (now - hits[0])
        hits.append(now)
        return 0


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
        raise InputError("No photo was received. Choose your photo again." if field == "photo"
                         else f"The {field} image was missing. Start the book again.")
    kind = sniff_image(data)
    if kind is None:
        raise InputError("Upload a JPEG, PNG, or WebP photo (HEIC from iPhones is not supported).")
    return data, kind


def generate_image(prompt, image, kind, size=PAGE_SIZE):
    """Exactly one image API call per request; no retries or loops."""
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
        raise RuntimeError(msg)
    return "data:image/png;base64," + resp.json()["data"][0]["b64_json"]


def limited():
    wait = seconds_until_allowed(client_ip())
    if not wait:
        return None
    minutes = int(wait // 60) + 1
    return jsonify(error=f"You've reached the limit of {RATE_LIMIT_PER_HOUR} images per hour. "
                         f"Try again in {minutes} minute{'s' if minutes != 1 else ''}."), 429


@app.get("/")
def index():
    return render_template("index.html", pages=PAGES)


@app.post("/reference")
def reference():
    """Step 0: turn the uploaded photo into one cast reference (Jack and his mother) that every page reuses."""
    try:
        data, kind = read_image("photo")
    except InputError as e:
        return jsonify(error=str(e)), 400
    if (resp := limited()):
        return resp
    try:
        return jsonify(image=generate_image(REFERENCE_PROMPT, data, kind, size=REFERENCE_SIZE))
    except RuntimeError as e:
        return jsonify(error=str(e)), 502


@app.post("/page")
def page():
    """Draw one page from the character reference, or edit an existing page when `change` is given."""
    p = PAGES_BY_ID.get(request.form.get("page"))
    if p is None:
        return jsonify(error="Unknown page. Reload and try again."), 400
    change = (request.form.get("change") or "").strip()
    if len(change) > 200:
        return jsonify(error="Keep the change to 200 characters or fewer."), 400
    try:
        if change:
            data, kind = read_image("current")
            prompt = edit_prompt(change)
        else:
            data, kind = read_image("reference")
            prompt = page_prompt(p)
    except InputError as e:
        return jsonify(error=str(e)), 400
    if (resp := limited()):
        return resp
    try:
        return jsonify(image=generate_image(prompt, data, kind))
    except RuntimeError as e:
        return jsonify(error=str(e)), 502


# ---------- PDF ----------

PAGE_W, PAGE_H = 432, 648  # 6 x 9 inches, same 2:3 shape as the art
INK = (0.08, 0.13, 0.24)
CREAM = (1, 0.99, 0.96)


def decode_data_url(url):
    if not isinstance(url, str) or "," not in url:
        raise InputError("A page image is missing. Draw every page before downloading.")
    data = base64.b64decode(url.split(",", 1)[1])
    if sniff_image(data) is None:
        raise InputError("A page image could not be read. Redraw it and try again.")
    return data


def draw_story_text(c, text, zone, tone):
    size, lead, pad = 22, 28, 16
    lines = simpleSplit(text, "Times-Bold", size, PAGE_W - 2 * 36 - 2 * pad)
    box_h = len(lines) * lead + 2 * pad
    y0 = 40 if zone == "bottom" else PAGE_H - 40 - box_h
    fg, bg = (INK, CREAM) if tone == "light" else (CREAM, INK)
    c.saveState()
    c.setFillColorRGB(*bg)
    c.setFillAlpha(0.82)
    c.roundRect(36, y0, PAGE_W - 72, box_h, 14, stroke=0, fill=1)
    c.restoreState()
    c.setFillColorRGB(*fg)
    c.setFont("Times-Bold", size)
    y = y0 + box_h - pad - size + 4
    for line in lines:
        c.drawCentredString(PAGE_W / 2, y, line)
        y -= lead


def jack_portrait(reference_img):
    """Jack stands on the left half of the cast reference; crop him out for the About Me page."""
    im = Image.open(io.BytesIO(reference_img)).convert("RGB")
    w, h = im.size
    half = im.crop((0, 0, w // 2, h))
    target_w = half.height * 2 // 3  # 2:3 portrait, centered on Jack
    left = max(0, (half.width - target_w) // 2)
    return half.crop((left, 0, left + min(target_w, half.width), half.height))


def build_pdf(images, reference_img, name, age, favorites):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Jack and the Beanstalk, starring {name}")
    for p, img in zip(PAGES, images):
        c.drawImage(ImageReader(io.BytesIO(img)), 0, 0, PAGE_W, PAGE_H)  # full bleed
        draw_story_text(c, p["text"], p["text_zone"], p["tone"])
        c.showPage()

    # Last page: About Me
    c.setFillColorRGB(*CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColorRGB(*INK)
    c.setFont("Times-Bold", 34)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 70, "About Me")
    if reference_img:
        c.drawImage(ImageReader(jack_portrait(reference_img)), PAGE_W / 2 - 100, PAGE_H - 400, 200, 300)
    y = PAGE_H - 445
    c.setFont("Times-Bold", 26)
    c.drawCentredString(PAGE_W / 2, y, name)
    y -= 34
    c.setFont("Times-Roman", 17)
    if age:
        c.drawCentredString(PAGE_W / 2, y, f"Age {age}")
        y -= 30
    if favorites:
        c.setFont("Times-Italic", 15)
        c.drawCentredString(PAGE_W / 2, y, "My favorite things")
        y -= 22
        c.setFont("Times-Roman", 15)
        for line in simpleSplit(favorites, "Times-Roman", 15, PAGE_W - 96)[:6]:
            c.drawCentredString(PAGE_W / 2, y, line)
            y -= 20
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


@app.post("/pdf")
def pdf():
    body = request.get_json(silent=True) or {}
    name = str(body.get("name") or "").strip()[:40]
    age = str(body.get("age") or "").strip()[:3]
    favorites = str(body.get("favorites") or "").strip()[:300]
    if not name:
        return jsonify(error="Type the child's name for the About Me page."), 400
    if age and not age.isdigit():
        return jsonify(error="Age should be a number."), 400
    try:
        images = [decode_data_url((body.get("pages") or {}).get(p["id"])) for p in PAGES]
        ref = decode_data_url(body["reference"]) if body.get("reference") else None
    except InputError as e:
        return jsonify(error=str(e)), 400
    except ValueError:
        return jsonify(error="A page image could not be read. Redraw it and try again."), 400
    return send_file(build_pdf(images, ref, name, age, favorites), mimetype="application/pdf",
                     as_attachment=True, download_name="JackAndTheBeanstalk.pdf")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
