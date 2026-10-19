import base64
import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()  # reads .env locally; on Render the key comes from its environment settings

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload cap

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-1-mini")
API_URL = "https://api.openai.com/v1/images/edits"

# The two required scenes. The scene spec is sent to the model and shown as the caption.
SCENES = {
    "planting": "Jack is planting the magic seeds in the soil outside his cottage, kneeling in the dirt "
                "with a small handful of glowing beans, a tiny sprout just starting to rise.",
    "climbing": "Jack is climbing up the giant beanstalk, gripping the thick green vines with both hands, "
                "high above the ground with clouds around him and a distant castle in the sky above.",
}

STYLES = {
    "pixar": "3D animated movie style (Pixar-like), soft lighting, smooth shading",
    "comic": "bold comic-book style with thick ink outlines and flat colors",
    "anime": "anime style with clean linework and cel shading",
    "storybook": "hand-painted children's storybook illustration, watercolor texture",
}

INTENSITY = {
    "subtle": "Keep proportions and details very close to the real face; only lightly stylized.",
    "medium": "Clearly cartoonish, but keep the face's distinguishing features.",
    "strong": "Strongly stylized and exaggerated, but still recognizably the same person.",
}


def build_prompt(scene_spec, style, intensity, outline):
    return (
        f"Redraw the person in the provided photo as a cartoon character, and place them in this scene. "
        f"Scene: {scene_spec} The character is Jack from the fairy tale 'Jack and the Beanstalk'. "
        f"Art style: {STYLES[style]}. {INTENSITY[intensity]} Outline thickness: {outline}. "
        f"IMPORTANT: preserve this person's identity exactly: same face shape, eyes, nose, mouth, eyebrows, "
        f"skin tone, hair color and hairstyle, facial hair, glasses, and apparent age and gender. "
        f"The scene must show exactly what the scene description says and nothing contradictory. "
        f"Only one main character. No text, captions, or watermarks in the image."
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
