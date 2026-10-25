# Prompts (draft 2, for testing in the OpenAI Playground)

Paste these into the Playground by hand before they go into the code.
After each try, note what was wrong under "Playground notes" and revise.

## Settings to use in the Playground

- Model: `gpt-image-2.5-flare`. Also try `gpt-image-2.5-sunburst` on the page prompts, since it is the editing-focused one.
- Size: 1024 x 1536 (portrait, one book page)
- Quality: low while experimenting; try medium once a prompt works
- Mode: edit (attach an image) for every prompt below

## The style string

Used word for word in every call. It never changes mid-book.

```
Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
```

## Step 0: character reference (attach: the uploaded photo)

Made once per book. Every page then uses this image as its one reference, so Jack's face
and clothes stay the same on every page.

```
Character reference sheet for a children's picture book. Turn the child in the attached photo into Jack, the hero of "Jack and the Beanstalk".
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
Full body, standing, facing the viewer, arms relaxed, on a plain light-grey background.
Keep the child's face shape, eye shape and color, skin tone, hair color and hairstyle, and any glasses or freckles, rendered in the style above, never photographic.
Outfit: patched brown wool tunic, rope belt, green trousers, worn leather boots.
No text, letters, or labels anywhere in the image.
```

## Pages (attach: the character reference from step 0)

Every page prompt has the same opening and closing; only the scene, mood, and composition lines change.

### Page 1: the empty cupboard

Story text (drawn by the PDF layer, not the model): "Jack and his mother had nothing left to sell but Milky-White."

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The boy in the attached reference image is Jack. Keep his face, hair, and outfit exactly as in the reference.
Scene: Jack and his mother stand in a bare cottage kitchen beside an empty, open cupboard. Through the open door, Milky-White the cow is visible outside.
Jack's full face is front-lit, and he is looking at his mother.
Mood: Worried and sad. Jack's mother looks tired and anxious, her shoulders slumped. Jack looks up at her with a worried face. No smiles, but gentle rather than frightening, since this is a children's book.
Composition: keep the lower third of the image quiet and uncluttered (plain floorboards) so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 2: the trade

Story text: "Five magic beans, said the old man. For one cow."

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The boy in the attached reference image is Jack. Keep his face, hair, and outfit exactly as in the reference.
Scene: a dirt road leading to market. An old man holds out five coloured beans in his open palm. Jack holds Milky-White the cow by a rope.
Jack is in three-quarter view, wearing the same clothes as in the reference.
Mood: Jack is curious and tempted, eyes wide at the beans. The old man smiles slyly, as if he knows a secret.
Composition: keep the sky in the top third of the image clear and simple so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 3: out the window

Story text: "Beans! she cried. And out the window they went."

```
Children's picture-book page illustration.
Style: Modern 3D animated feature — rounded forms, large expressive eyes, soft rim light.
The boy in the attached reference image is Jack. Keep his face, hair, and outfit exactly as in the reference.
Scene: the cottage at dusk. Jack's mother throws the beans out of a window, and they scatter into the garden below. Jack stands in the doorway, watching.
Use a darker dusk palette than the daytime pages: deep blues and purples, with warm light from the window.
Mood: Jack's mother is angry and frustrated. Jack looks shocked and dismayed, his mouth open. No smiles.
Composition: keep the dark grass in the lower third calm and uncluttered so text can sit there.
Do not draw any text, letters, or signs.
```

### Page 4 (later): the beanstalk at dawn

Not built yet. It follows the same template, with "Scene:" and "Composition:" lines changed.

## Playground notes

| Try | Prompt | What came back | What to change |
|-----|--------|----------------|----------------|
| 1 | Page 1 (draft 1) | Jack and his mother look happy, which contradicts "nothing left to sell" | Added a Mood line to every page: worried on page 1, tempted on page 2, angry and shocked on page 3 |
|     |        |                |                |
