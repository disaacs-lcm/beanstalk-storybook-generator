# To do

What in this build still needs work.

- The prompts have not been tested in the OpenAI Playground yet. Everything in `PROMPTS.md` is a first draft.
- Jack's face across pages is only as consistent as the character reference. I haven't checked yet whether his face drifts between pages 1 and 3.
- Faces come from one reference image (Jack and his mother, neutral expressions). Everything else that recurs (clothes, Milky-White, the cottage, the beans) only has a written description. I haven't checked yet whether the descriptions alone keep the cow and the beans looking the same.
- The cottage has one fixed description (small, one-story, thatched) shared by pages 1 and 3. The first draft drew it two stories tall on page 3, so this needs checking in the Playground.
- The prompts ask the model to leave a calm area for the story text, but nothing checks that it did. The text panel can end up covering a face.
- Page 4 (the beanstalk at dawn) isn't built. The planting and climbing scenes from the first app still need to be moved into the book as pages.
- The story assumes a boy named Jack. Girl and gender-neutral versions are coming later in the specs.
- The web preview's cover title uses Fraunces, but the PDF cover uses Andika Bold, because Fraunces only ships as a variable font and those are unreliable in reportlab. A static Fraunces build would make them match.
- Nothing is saved on the server, so refreshing the page loses the book.
- I added a front cover (not in the spec): its art comes from the face reference, and the title and name are drawn by the PDF. A back cover would finish the book.
- The per-visitor limit (15 images an hour) lives in memory and resets whenever Render restarts the service.
