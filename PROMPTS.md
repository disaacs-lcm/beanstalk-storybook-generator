# Prompts (for testing in the OpenAI Playground)

Generated from `app.py` by `export_prompts.py`, so these are exactly what the app sends.
Paste them into the Playground by hand. After each try, add a row under "Playground notes".

## Settings to use in the Playground

- Model: `gpt-image-2.5-flare`. Also try `gpt-image-2.5-sunburst` on the page prompts, since it is the editing-focused one.
- Size: 1536 x 1024 for the face reference, 1024 x 1536 for pages
- Quality: low while experimenting; try medium once a prompt works
- Mode: edit (attach an image) for every prompt below

## The style string

Used word for word in every call. It never changes mid-book.

```
Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
```

## What recurs, and how it stays consistent

| Element | Pages | How |
|---|---|---|
| jack | 1, 2, 3 | Face from the reference image, plus the description |
| mother | 1, 3 | Face from the reference image, plus the description |
| cow | 1, 2 | Description only |
| cottage | 1, 3 | Description only |
| beans | 2, 3 | Description only |

Descriptions, used word for word on every page where the element appears:

- **jack**: Jack wears a patched brown wool tunic, a rope belt, green trousers, and worn leather boots.
- **mother**: Jack's mother is a slim woman in her late thirties with the same skin tone and hair color as Jack. Her hair is tied back in a loose bun under a faded blue headscarf, and she wears a patched grey-blue dress and a cream apron.
- **cow**: Milky-White is a gentle, thin white dairy cow with a few soft brown patches, a pink nose, short curved horns, and a frayed rope halter.
- **cottage**: The cottage is a small one-story stone cottage with a thatched roof, a wooden front door, and one small window beside the door (one story only, no upper floor).
- **beans**: The magic beans are five smooth beans, each a different bright color (red, orange, green, blue, and purple), each about the size of a fingernail, with a faint sparkle.

## Step 0: face reference (attach: the uploaded photo)

Made once per book: Jack's face on the left, his mother's on the right, both neutral. Pages with both of
them attach the whole image; pages with only Jack attach its left half.

```
Character reference for a children's picture book "Jack and the Beanstalk". Draw the person in the attached photo as Jack, the hero of the story, at the same age they appear in the photo.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
Two head-and-shoulders portraits side by side on a plain light-grey background: Jack on the left, his mother on the right. Both face the viewer with a calm, neutral expression.
Jack: keep the person's face shape, eye shape and color, skin tone, hair color and hairstyle, and any glasses or freckles, rendered in the style above, never photographic.
Jack's mother is a slim woman in her late thirties with the same skin tone and hair color as Jack. Her hair is tied back in a loose bun under a faded blue headscarf, and she wears a patched grey-blue dress and a cream apron.
No text, letters, or labels anywhere in the image.
```

## Pages (attach: the face reference from step 0)

### Page 1: The empty cupboard

Attach: the whole reference. Story text (drawn by the PDF layer, not the model): Jack and his mother had nothing left to sell but Milky-White.

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The attached reference shows the faces of Jack (left in the reference) and Jack's mother (right in the reference). Keep their faces and hair exactly as in the reference; their expressions follow the Mood line below.
These appear elsewhere in the book too, so draw them exactly as described:
- Jack wears a patched brown wool tunic, a rope belt, green trousers, and worn leather boots.
- Jack's mother is a slim woman in her late thirties with the same skin tone and hair color as Jack. Her hair is tied back in a loose bun under a faded blue headscarf, and she wears a patched grey-blue dress and a cream apron.
- The cottage is a small one-story stone cottage with a thatched roof, a wooden front door, and one small window beside the door (one story only, no upper floor).
- Milky-White is a gentle, thin white dairy cow with a few soft brown patches, a pink nose, short curved horns, and a frayed rope halter.
Scene: inside the cottage. Jack and his mother stand in its bare kitchen beside an empty, open cupboard. Through the open front door, Milky-White is visible outside.
Jack's full face is front-lit, and he is looking at his mother.
Mood: Worried and sad. Jack's mother looks tired and anxious, her shoulders slumped. Jack looks up at her with a worried face. No smiles, but gentle rather than frightening, since this is a children's book.
Composition: keep the lower third of the image quiet and uncluttered (plain floorboards) so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 2: The trade

Attach: the left half of the reference (Jack only). Story text (drawn by the PDF layer, not the model): “Five magic beans,” said the old man. “For one cow.”

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The attached reference shows Jack's face. Keep his face and hair exactly as in the reference; his expression follows the Mood line below.
These appear elsewhere in the book too, so draw them exactly as described:
- Jack wears a patched brown wool tunic, a rope belt, green trousers, and worn leather boots.
- Milky-White is a gentle, thin white dairy cow with a few soft brown patches, a pink nose, short curved horns, and a frayed rope halter.
- The magic beans are five smooth beans, each a different bright color (red, orange, green, blue, and purple), each about the size of a fingernail, with a faint sparkle.
Scene: a dirt road leading to market. An old man holds out the five magic beans in his open palm. Jack holds Milky-White by her rope halter.
Jack is in three-quarter view.
Mood: Jack is curious and tempted, eyes wide at the beans. The old man smiles slyly, as if he knows a secret.
Composition: keep the sky in the top third of the image clear and simple so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 3: Out the window

Attach: the whole reference. Story text (drawn by the PDF layer, not the model): “Beans!” she cried. And out the window they went.

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The attached reference shows the faces of Jack (left in the reference) and Jack's mother (right in the reference). Keep their faces and hair exactly as in the reference; their expressions follow the Mood line below.
These appear elsewhere in the book too, so draw them exactly as described:
- Jack wears a patched brown wool tunic, a rope belt, green trousers, and worn leather boots.
- Jack's mother is a slim woman in her late thirties with the same skin tone and hair color as Jack. Her hair is tied back in a loose bun under a faded blue headscarf, and she wears a patched grey-blue dress and a cream apron.
- The cottage is a small one-story stone cottage with a thatched roof, a wooden front door, and one small window beside the door (one story only, no upper floor).
- The magic beans are five smooth beans, each a different bright color (red, orange, green, blue, and purple), each about the size of a fingernail, with a faint sparkle.
Scene: outside the cottage, at dusk. Jack's mother leans out of the small ground-floor window and throws the magic beans, which scatter into the garden in front of the cottage. Jack stands in the open front doorway, watching.
Use a darker dusk palette than the daytime pages: deep blues and purples, with warm light from the window.
Mood: Jack's mother is angry and frustrated. Jack looks shocked and dismayed, his mouth open. No smiles.
Composition: keep the dark grass in the lower third calm and uncluttered so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 4 (later): the beanstalk at dawn

Not built yet. It will be one more entry in `PAGES` in `app.py`.

## Playground notes

| Try | Prompt | What came back | What to change |
|-----|--------|----------------|----------------|
| 1 | Page 1 (draft 1) | Jack and his mother look happy, which contradicts "nothing left to sell" | Added a Mood line to every page: worried on page 1, tempted on page 2, angry and shocked on page 3 |
| 2 | Page 3 (draft 2) | The cottage came out two stories tall | Added one fixed cottage description (small, one-story, thatched, "no upper floor") reused on pages 1 and 3; the mother now leans out of a ground-floor window |
| 3 | Pages 1 and 3 (draft 2) | The mother looks like a different woman on each page | Put her in the reference: one image with Jack on the left and his mother on the right, plus a fixed description of her, reused on every page |
| 4 | All pages (draft 3) | A full-body two-person reference shrinks the faces and covers more than needed | Reference is now neutral face portraits only, attached only for the faces a page needs; the cow, cottage, beans and clothes use fixed descriptions on every page they appear |
| 5 | Face reference (live site) | OpenAI's safety system rejected the request | Reworded step 0: "the person in the attached photo ... at the same age they appear" instead of "turn the child into Jack"; errors now name the step that failed |
|     |        |                |                |
