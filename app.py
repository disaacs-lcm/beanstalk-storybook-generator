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


@app.get("/")
def index():
    return render_template("index.html", scenes=SCENES, styles=list(STYLES))


@app.post("/generate")
def generate():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return jsonify(error="Server is missing OPENAI_API_KEY."), 500

    photo = request.files.get("photo")
    scene_id = request.form.get("scene")
    style = request.form.get("style", "pixar")
    intensity = request.form.get("intensity", "medium")
    outline = request.form.get("outline", "medium")
    if not photo or scene_id not in SCENES or style not in STYLES or intensity not in INTENSITY \
            or outline not in ("thin", "medium", "thick"):
        return jsonify(error="Invalid request."), 400
    if photo.mimetype not in ("image/jpeg", "image/png", "image/webp"):
        return jsonify(error="Upload a JPEG, PNG, or WebP photo."), 400

    scene_spec = SCENES[scene_id]
    prompt = build_prompt(scene_spec, style, intensity, outline)

    # Exactly one API call per request; no retries or loops.
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}"},
        data={"model": IMAGE_MODEL, "prompt": prompt, "size": "1024x1024", "quality": "low", "n": "1"},
        files={"image": (photo.filename or "photo", photo.read(), photo.mimetype)},
        timeout=170,
    )
    if resp.status_code != 200:
        msg = resp.json().get("error", {}).get("message", "Image API error") if resp.content else "Image API error"
        return jsonify(error=msg), 502
    b64 = resp.json()["data"][0]["b64_json"]
    return jsonify(image=f"data:image/png;base64,{b64}", caption=scene_spec)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
