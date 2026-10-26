# To do

What in this build still needs work.

## Consistency across pages
- Jack's face comes from one reference image that every page reuses. I've only tested with a few photos, so I don't yet know how often his face drifts between page 1 and page 3 for other kids.
- His mother is in the same reference, so her face should hold. Her clothes, Milky-White, the cottage, and the beans are kept the same only by written descriptions. If Milky-White's patches move between pages 1 and 2, she needs her own reference image.
- The cottage was drawn two stories tall on page 3 in an early draft. A fixed "one-story" description fixed it in the Playground, but nothing checks it on every book.

## Layout
- The prompts ask the model to leave a calm area for the story text, but nothing checks that it did. The text panel can end up covering a face, and the only fix right now is to redraw the page.
- The web cover title uses Fraunces, but the PDF cover uses Andika Bold, because Fraunces only comes as a variable font and reportlab handles those badly. A static Fraunces file would make them match.

## Story
- Page 4 (the beanstalk at dawn) isn't built yet. The planting and climbing scenes from the first app still need to become pages, on the way to 20.
- The story assumes a boy named Jack. Girl and gender-neutral versions come later in the specs.
- The front cover is an extra. A back cover would finish the book.

## Reliability and cost
- OpenAI's safety filter once refused the reference step when the prompt said "turn the child into Jack". Rewording it fixed that, but some photos may still be refused. The app explains the error but offers no other path.
- Nothing is saved on the server. Refreshing the page loses the book, and making it again costs another 5 images.
- Images are drawn at low quality to keep each book to a few cents. I haven't compared low and medium quality side by side to see if medium is worth the cost.
- The limit of 15 images per visitor per hour lives in memory, so it resets whenever Render restarts the service.
