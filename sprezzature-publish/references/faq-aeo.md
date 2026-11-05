# FAQ for answer engines: where it goes, how an answer is shaped

## When to consult this file

- Somebody asks "one FAQ on the home page, or one per page?".
- Somebody asks whether the `FAQPage` markup should be "centralised".
- An answer drafted by `sprezzature-publish-faq` has to be rewritten by hand,
  and the rewrite needs a target.
- `FAQ005` fired and the author wants to know why.

For the rules and their authorities, see `audit-site.md`. For the wider
SEO / GEO picture, see `seo-essentials.md`.

## Placement: one FAQ per money page, never the same question twice

- **The answer belongs on the page that answers the query.** An answer
  engine quotes a passage of the page it retrieved for the query. Somebody
  asking about a course lands on the course page, not on the home page; an
  answer about the course sitting on the home page is quoted less, or not
  at all.
- **Every money page gets its own FAQ** (`FIND005`): the page carrying a
  declared CTA is where the reader hesitates before clicking, so that is
  where the objections are answered.
- **No question is repeated across pages** (`FAQ004`). The same question
  on four pages is the doorway pattern of Google's spam policies, in
  miniature.
- **The markup sits on the page it describes, and only there.** Google's
  structured-data guidelines refuse markup for content the page does not
  show (`FAQ002`, `FAQ003`). "Centralising" the `FAQPage` markup on the home
  page for questions shown elsewhere breaks that rule.
- **What is centralised is the making, not the output**: one component
  draws every FAQ, one function builds each page's markup from that page's
  own text, one place holds the text. `llms.txt` links each FAQ;
  `llms-full.txt` carries them all.
- **Pages that do not get one**: long-form articles (they are a single
  document, often narrated), legal notices, error pages, reading lists
  where the questions would be invented.

Google stopped showing FAQ rich results on 2026-05-07. The visible text is
the deliverable; the markup is a copy of it, kept for the engines that
still read schema.org.

## Anatomy of an answer

The drafting prompt (`scripts/prompts/faq_answer.yaml`) and `FAQ005` hold
the same shape:

1. **The first sentence answers and names the organisation.** It is the
   sentence an engine lifts alone; "You pick a slot in my calendar" says
   nothing out of context, "To book a call with Acme, you pick a slot"
   does. A product name alone ("the Enterprise AI bootcamp") is not enough:
   say whose.
2. **One supporting fact**, with its source a click away: a number the site
   states, a quotation, a named client or venue.
3. **Three sentences at most, eighty words at most.** On the calibration
   site the rewritten answers ran from 27 to 67 words.
4. **No call to action inside the answer.** The buttons follow the FAQ.
5. **Close the section with a heading.** A parser reads an answer up to the
   next heading: a call to action after the last question, with no heading
   of its own, is swallowed into that answer. `_content` now also ends the
   answer when the FAQ's container closes, but a page read by somebody
   else's parser does not get that courtesy.
6. **Keep the markup character for character.** A no-break space before a
   French `?` that the markup turns into a plain space is a disagreement
   the strict comparison of a validator sees.

## Questions a services firm is asked

The built-in checklist was written for products ("How much does it cost?",
"What does it need to run?"). For a firm selling work rather than software,
the questions that decided were:

- what each offer *is*, one question per offer, phrased with the firm's
  name ("What does Acme build?") so the question itself is quotable;
- who a programme is for, what it contains, how long it lasts;
- which clients, which projects, what clients say (quotations, attributed);
- how the price is set (by quote, after what), what happens on booking;
- what happens to the client's data;
- for a secondary "star on GitHub" CTA: whether the tools can be tried
  before buying, and why the code is open. The second ends on what a star
  actually does (it tells other developers a repository is useful), right
  above the button.

## The calibration site, 2026-11-05

deraison.ai, a PHP site with no Markdown source, read through a static
mirror of the local server. What it taught, now in the code:

| Seen | Now |
|---|---|
| The last answer swallowed the CTA after it. | The answer ends when the FAQ's container closes. |
| An `<h3>` inside `<summary>` was read twice. | The `<details>` path alone reads it. |
| Extracted answers quoted bibliography notes. | Passages under reference headings leave the corpus. |
| Answers fine to a human, weak out of context. | `FAQ005`: length, sentence count, organisation named first. |

Still open: `FAQ001` warns on a count the page shows but never writes ("36
talks" on a page that lists thirty-six). Derived counts are facts; the rule
cannot tell them from invented ones yet.
