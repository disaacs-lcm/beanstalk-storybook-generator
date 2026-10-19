import base64
import os
import threading
import time
from collections import defaultdict, deque

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()  # reads .env locally; on Render the key comes from its environment settings

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload cap

# GPT Image 2.5 "flare": same token price as "sunburst"; quality "low" keeps each image around a cent.
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2.5-flare")
API_URL = "https://api.openai.com/v1/images/edits"

# Per-visitor limit on images (each click makes two). Kept in memory, so it resets when the server restarts.
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "6"))
_hits = defaultdict(deque)
_hits_lock = threading.Lock()

# The two required scenes. The scene spec is sent to the model and shown as the caption.
SCENES = {
    "planting": "Jack is planting the magic seeds in the soil outside his cottage, kneeling in the dirt "
                "with a small handful of glowing beans, a tiny sprout just starting to rise.",
    "climbing": "Jack is climbing up the giant beanstalk, gripping the thick green vines with both hands, "
                "high above the ground with clouds around him and a distant castle in the sky above.",
}

STYLES = {
    "pixar": "a 3D animated feature-film character render (Pixar-like), with stylized proportions, "
             "sculpted simplified features and soft painted lighting",
    "comic": "a hand-inked comic-book illustration with bold black ink outlines, flat color fills and halftone shading",
    "anime": "a 2D anime illustration with clean linework, large expressive eyes and flat cel shading",
    "storybook": "a hand-painted children's storybook illustration with visible brush strokes and watercolor texture",
}

INTENSITY = {
    "subtle": "Lightly stylized: realistic proportions, but every surface is drawn or painted, never photographic.",
    "medium": "Clearly cartoonish: simplified shapes, slightly enlarged head and eyes.",
    "strong": "Strongly exaggerated: big head, big expressive eyes, simplified bold shapes.",
}


def build_prompt(scene_spec, style, intensity, outline):
    return (
        f"Create a brand-new illustration of Jack from the fairy tale 'Jack and the Beanstalk'. "
        f"Scene: {scene_spec} "
        f"Art style: {STYLES[style]}. {INTENSITY[intensity]} Outline thickness: {outline}. "
        f"The attached photo is ONLY a reference for who Jack looks like. Do not edit, trace, or paste the photo. "
        f"Draw the face as a cartoon: no photorealistic skin, pores, or photographic lighting anywhere in the image. "
        f"Do not copy the photo's pose, crop, camera angle, head size, background or clothing. "
        f"Instead, show Jack's whole body in the pose the scene requires, wearing a simple storybook "
        f"peasant outfit, with his head about one-fifth to one-quarter of his body height, "
        f"inside the full scene and its background. "
        f"Carry over these identity features from the photo in cartoon form: face shape, eye shape and color, "
        f"nose, eyebrows, skin tone, hair color and hairstyle, facial hair, glasses, and apparent age and gender. "
        f"The picture must show exactly what the scene says and nothing that contradicts it. "
        f"One main character. No text, captions, or watermarks in the image."
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


@app.get("/")
def index():
    return render_template("index.html", scenes=SCENES, styles=list(STYLES))


@app.post("/generate")
def generate():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return jsonify(error="Server is missing OPENAI_API_KEY."), 500

    scene_id = request.form.get("scene")
    style = request.form.get("style", "pixar")
    intensity = request.form.get("intensity", "medium")
    outline = request.form.get("outline", "medium")
    for name, value, allowed in (("scene", scene_id, SCENES), ("style", style, STYLES),
                                 ("intensity", intensity, INTENSITY), ("outline", outline, ("thin", "medium", "thick"))):
        if value not in allowed:
            return jsonify(error=f"Unknown {name} setting: {value!r}. Reload the page and try again."), 400

    # `if not photo` is False for an empty filename, so check for None and read the bytes instead.
    photo = request.files.get("photo")
    data = photo.read() if photo is not None else b""
    if not data:
        return jsonify(error="No photo was received. Choose your photo again."), 400
    kind = sniff_image(data)
    if kind is None:
        return jsonify(error="Upload a JPEG, PNG, or WebP photo (HEIC from iPhones is not supported)."), 400
    mimetype, ext = kind

    # Checked last, so rejected uploads don't use up a visitor's allowance.
    wait = seconds_until_allowed(client_ip())
    if wait:
        minutes = int(wait // 60) + 1
        return jsonify(error=f"You've reached the limit of {RATE_LIMIT_PER_HOUR} images per hour. "
                             f"Try again in {minutes} minute{'s' if minutes != 1 else ''}."), 429

    scene_spec = SCENES[scene_id]
    prompt = build_prompt(scene_spec, style, intensity, outline)

    # Exactly one API call per request; no retries or loops.
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}"},
        data={"model": IMAGE_MODEL, "prompt": prompt, "size": "1024x1024", "quality": "low", "n": "1"},
        files={"image": (f"photo.{ext}", data, mimetype)},
        timeout=170,
    )
    if resp.status_code != 200:
        msg = resp.json().get("error", {}).get("message", "Image API error") if resp.content else "Image API error"
        return jsonify(error=msg), 502
    b64 = resp.json()["data"][0]["b64_json"]
    return jsonify(image=f"data:image/png;base64,{b64}", caption=scene_spec)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
