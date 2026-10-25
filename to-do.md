# To do

What in this build still needs work.

- The prompts have not been tested in the OpenAI Playground yet. Everything in `PROMPTS.md` is a first draft.
- Jack's face across pages is only as consistent as the character reference. I haven't checked yet whether his face drifts between pages 1 and 3.
- The mother appears on pages 1 and 3 but has no reference image, so she will probably look like a different woman on each page. She needs her own reference, or a combined Jack-and-mother reference.
- The old man and Milky-White also have no references. Milky-White is seen on pages 1 and 2 and could change color or size between them.
- The prompts ask the model to leave a calm area for the story text, but nothing checks that it did. The text panel can end up covering a face.
- Page 4 (the beanstalk at dawn) isn't built. The planting and climbing scenes from the first app still need to be moved into the book as pages.
- The story assumes a boy named Jack. Girl and gender-neutral versions are coming later in the specs.
- The PDF uses the built-in Times font. A rounder storybook font would read better for kids.
- Nothing is saved on the server, so refreshing the page loses the book.
- The per-visitor limit (12 images an hour) lives in memory and resets whenever Render restarts the service.
