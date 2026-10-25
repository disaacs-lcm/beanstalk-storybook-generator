# Prompts (for testing in the OpenAI Playground)

Generated from `app.py` by `export_prompts.py`, so these are exactly what the app sends.
Paste them into the Playground by hand. After each try, add a row under "Playground notes".

## Settings to use in the Playground

- Model: `gpt-image-2.5-flare`. Also try `gpt-image-2.5-sunburst` on the page prompts, since it is the editing-focused one.
- Size: 1536 x 1024 for the cast reference, 1024 x 1536 for pages
- Quality: low while experimenting; try medium once a prompt works
- Mode: edit (attach an image) for every prompt below

## The style string

Used word for word in every call. It never changes mid-book.

```
Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
```

## Step 0: cast reference (attach: the uploaded photo)

Made once per book: Jack on the left, his mother on the right. Every page attaches this one image,
so both of them look the same on every page.

```
Character reference sheet for a children's picture book "Jack and the Beanstalk". Turn the child in the attached photo into Jack.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
Two full-body characters side by side, standing, facing the viewer, arms relaxed, on a plain light-grey background: Jack on the left, his mother on the right.
Jack: keep the child's face shape, eye shape and color, skin tone, hair color and hairstyle, and any glasses or freckles, rendered in the style above, never photographic. Outfit: patched brown wool tunic, rope belt, green trousers, worn leather boots.
Jack's mother: a slim woman in her late thirties with the same skin tone and hair color as Jack, her hair tied back in a loose bun under a faded blue headscarf, wearing a patched grey-blue dress and a cream apron.
No text, letters, or labels anywhere in the image.
```

## Pages (attach: the cast reference from step 0)

### Page 1: The empty cupboard

Story text (drawn by the PDF layer, not the model): Jack and his mother had nothing left to sell but Milky-White.

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The attached reference shows Jack (left) and his mother (right). Whenever they appear, keep their faces, hair, and clothes exactly as in the reference.
Scene: inside a small one-story stone cottage with a thatched roof, a wooden front door, and one small window beside the door (one story only, no upper floor). Jack and his mother stand in its bare kitchen beside an empty, open cupboard. Through the open front door, Milky-White the cow is visible outside.
Jack's full face is front-lit, and he is looking at his mother.
Mood: Worried and sad. Jack's mother looks tired and anxious, her shoulders slumped. Jack looks up at her with a worried face. No smiles, but gentle rather than frightening, since this is a children's book.
Composition: keep the lower third of the image quiet and uncluttered (plain floorboards) so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 2: The trade

Story text (drawn by the PDF layer, not the model): “Five magic beans,” said the old man. “For one cow.”

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The attached reference shows Jack (left) and his mother (right). Whenever they appear, keep their faces, hair, and clothes exactly as in the reference.
Scene: a dirt road leading to market. An old man holds out five coloured beans in his open palm. Jack holds Milky-White the cow by a rope.
Jack is in three-quarter view, wearing the same clothes as in the reference.
Mood: Jack is curious and tempted, eyes wide at the beans. The old man smiles slyly, as if he knows a secret.
Composition: keep the sky in the top third of the image clear and simple so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 3: Out the window

Story text (drawn by the PDF layer, not the model): “Beans!” she cried. And out the window they went.

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The attached reference shows Jack (left) and his mother (right). Whenever they appear, keep their faces, hair, and clothes exactly as in the reference.
Scene: outside a small one-story stone cottage with a thatched roof, a wooden front door, and one small window beside the door (one story only, no upper floor), at dusk. Jack's mother leans out of the small ground-floor window and throws the beans, which scatter into the garden in front of the cottage. Jack stands in the open front doorway, watching.
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
|     |        |                |                |
