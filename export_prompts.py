"""Regenerate the prompt sections of PROMPTS.md from app.py, keeping the Playground notes table.

Run after changing any prompt:  uv run python export_prompts.py
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "unused")  # app.py only needs it for real API calls
import app  # noqa: E402

NOTES_HEADING = "## Playground notes"

with open("PROMPTS.md") as f:
    old = f.read()
notes = old[old.index(NOTES_HEADING):] if NOTES_HEADING in old else (
    f"{NOTES_HEADING}\n\n| Try | Prompt | What came back | What to change |\n|-----|--------|----------------|----------------|\n")

out = [
    "# Prompts (for testing in the OpenAI Playground)",
    "",
    "Generated from `app.py` by `export_prompts.py`, so these are exactly what the app sends.",
    "Paste them into the Playground by hand. After each try, add a row under \"Playground notes\".",
    "",
    "## Settings to use in the Playground",
    "",
    f"- Model: `{app.IMAGE_MODEL}`. Also try `gpt-image-2.5-sunburst` on the page prompts, since it is the editing-focused one.",
    f"- Size: {app.REFERENCE_SIZE.replace('x', ' x ')} for the cast reference, {app.PAGE_SIZE.replace('x', ' x ')} for pages",
    f"- Quality: {app.IMAGE_QUALITY} while experimenting; try medium once a prompt works",
    "- Mode: edit (attach an image) for every prompt below",
    "",
    "## The style string",
    "",
    "Used word for word in every call. It never changes mid-book.",
    "",
    "```", app.STYLE, "```",
    "",
    "## Step 0: cast reference (attach: the uploaded photo)",
    "",
    "Made once per book: Jack on the left, his mother on the right. Every page attaches this one image,",
    "so both of them look the same on every page.",
    "",
    "```", app.REFERENCE_PROMPT, "```",
    "",
    "## Pages (attach: the cast reference from step 0)",
    "",
]
for i, p in enumerate(app.PAGES, 1):
    out += [f"### Page {i}: {p['title']}", "",
            f"Story text (drawn by the PDF layer, not the model): {p['text']}", "",
            "```", app.page_prompt(p), "```", ""]
out += ["### Page 4 (later): the beanstalk at dawn", "",
        "Not built yet. It will be one more entry in `PAGES` in `app.py`.", "", notes]

with open("PROMPTS.md", "w") as f:
    f.write("\n".join(out))
print("PROMPTS.md updated")
