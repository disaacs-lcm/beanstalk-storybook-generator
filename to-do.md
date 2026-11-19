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
- Images are drawn at low quality to keep each book to a few cents. I haven't compared low and medium quality side by side to see if medium is worth the cost.

## Accounts, saving and progress (this iteration)
- Done: sign in with Google. Each account has one book, and its pictures and About Me details are saved in Postgres, so the book is still there after a refresh, a sign-out, or a redeploy.
- Done: the cast is drawn first. The cover and all three pages are then drawn at the same time on server threads, and each one is saved as soon as it's finished. Closing the tab doesn't stop the book.
- Done: a progress bar for each picture (waiting, drawing with seconds elapsed, done, failed) and an estimate of the time left, based on how long recent pictures took.
- Done: logging. Every request, image call (with its duration and outcome), sign-in and PDF is written to stdout for Render's log, and image calls, sign-ins and PDFs also go to an `events` table.
- Done: the rate limit is now per account and counted from the `events` table, so a restart no longer resets it.
- Done: `IMAGE_PROVIDER=fake` draws small placeholder pictures for free, to test the progress bar, the database and the PDF without spending tokens.
- One book per account. Making a new book replaces the old one, with no warning and no history. Several saved books, or at least an "are you sure?", should come next.
- Images are stored in the database as JPEGs (about 300 KB each, 1.5 MB per book). That's fine at class scale. Object storage (S3 or R2) would be better past a few hundred books.
- Render's free Postgres expires after 30 days, so the database needs a paid plan or a move before then.
- If Render restarts while a book is drawing, the unfinished pictures show as failed after 5 minutes and have to be redrawn. Nothing restarts them automatically.
- The progress bar is an estimate. The image API doesn't report progress during a call, so each bar fills based on elapsed time against recent averages and stops at 95% until the picture arrives.
- The user's real feedback (10 people) and the AI personas (10) haven't been folded into the story, art or layout yet.
