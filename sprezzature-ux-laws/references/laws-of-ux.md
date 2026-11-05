# Laws of UX: canonical set

The design heuristics curated by **Jon YABLONSKI** at
[lawsofux.com](https://lawsofux.com/) and in his book *Laws of UX*
(O'Reilly, 2020; 2nd ed. 2024). The site currently lists **30 laws**;
this file restates each one in the skill's house format
(**trigger → action → Tailwind / HTML hook**) so the skill can *act*
on them. Definitions in quotation marks are verbatim from the source.

This is the canonical set. The broader, cognitive-step-ordered list
(Anchoring, Reciprocity, Endowment, Curse of Knowledge, Default Bias,
…) lives in `references/ux-psychology.md` of the companion package
`sprezzature-ui`, not in this repository. The two are deliberately
overlapping: when both apply, prefer the canonical entry here for trigger
phrasing and defer to `ux-psychology.md` for application-time tradeoffs.

Attribution: concept names and the curated set are © Jon YABLONSKI
(CC-BY-NC-SA 4.0 on lawsofux.com; restatements without verbatim copy
are fair commentary). Two external citations chosen as further
reading: the Nielsen Norman Group article on the Aesthetic-Usability
Effect (Feb 2024, Kate MORAN & Kathryn WHITENTON) and the Wikipedia
article on the Robustness Principle (the latter useful because it
surfaces real-world critiques of Postel's Law that UX writers often
omit).

---

## 1. Perception: what the eye groups (Gestalt heritage)

| Law | Origin | Trigger | Action | Hook |
|---|---|---|---|---|
| **Law of Proximity** | Gestalt (early 20c.) | Form fields, list items, or icons with uneven gaps that bury the grouping | Tighten in-group gap; widen between-group gap by ~2× | `space-y-2` inside a group; `space-y-6` between groups |
| **Law of Common Region** | Gestalt | Visual groups defined only by faint dividers that disappear in dark mode | Wrap the group in a shared region (background, border, or card) | `rounded-2xl bg-surface-secondary p-4 dark:bg-surface-secondary-dark` |
| **Law of Similarity** | Gestalt | Items that share behaviour styled differently (button + link + chip) | Pick one visual treatment per behaviour and reuse it | Two `<button class="…same-base-classes…">` not "button + link + chip" |
| **Law of Uniform Connectedness** | Gestalt | A label that belongs to one input is closer to the next input | Wrap with `<label for>`, share a container, line up vertically | `<label class="block">…<input class="mt-1 …" /></label>` |
| **Law of Prägnanz** (simplicity) | WERTHEIMER, 1910 | Composition with five overlapping rectangles conveying one idea | Reduce to the simplest figure the eye can parse | Drop decorative SVGs; keep one icon per row |
| **Selective Attention** | BROADBENT 1958, CHERRY 1953, TREISMAN 1960 | Critical state hidden in colour alone (red badge, dot) | Add a second channel: icon **and** label, motion **and** colour | `<span class="text-red-700"><AlertIcon /> Failed</span>` not a red dot alone |

## 2. Decision: what the user picks

| Law | Origin | Trigger | Action | Hook |
|---|---|---|---|---|
| **Hick's Law** | HICK 1952, HYMAN 1953 | One screen offers > 7 top-level choices | Group, hide behind "More", or split across steps | `<details>` for advanced; segmented control caps at 5; highlight a recommended option |
| **Fitts's Law** | Paul M. FITTS, 1954 | Tap or click target smaller than 44 × 44 px, or far from where the pointer already is | Give every interactive control at least a 44 px hit area; keep frequent targets close | `min-h-11` (44 px on the Tailwind scale) on buttons and button-like links |
| **Choice Overload** | TOFFLER, *Future Shock* (1970) | Plan or pricing table with > 4 columns | Trim to 3 + "Contact us"; pre-recommend one; enable side-by-side compare | Centre column gets `ring-2 ring-brand-blue` and a "Most popular" pill |
| **Occam's Razor** | William of OCKHAM (c. 1287–1347) | Flow has steps that exist for internal reasons only | Cut any step that adds no user-visible value | If a step has zero inputs, delete it |
| **Pareto Principle** | Vilfredo PARETO (early 20c.) | Roadmap weighted by feature count, not impact | Identify the 20 % of paths handling 80 % of traffic; ship those first | Telemetry tag on top-5 paths; deprioritise the long tail |
| **Cognitive Bias** | TVERSKY & KAHNEMAN, 1972 | Designer assumes "users will…" with no evidence | Test with ≥ 5 outside users; seek contradictory data | Usability log per release; written confirmation-bias check |

## 3. Memory & cognition: what the user can hold

| Law | Origin | Trigger | Action | Hook |
|---|---|---|---|---|
| **Miller's Law** | George A. MILLER, 1956 | Phone number, code, IBAN rendered as one long run | Chunk into 3–4 groups of 3–4 chars | `+33 6 12 34 56 78`, `XXXX-XXXX-XXXX` |
| **Working Memory** | ATKINSON & SHIFFRIN, 1968 | User must remember a value from screen N to N+1 | Persist on-screen (sticky summary, breadcrumb with values, review step) | Sticky `<aside>` carrying cart total at every checkout step |
| **Chunking** | MILLER, 1956 | Long settings list with no headings | Group by topic; ≤ 7 items per group; one heading per group | `<section><h2>Account</h2><ul>…</ul></section>` |
| **Cognitive Load** | John SWELLER, 1988 (Cognitive Load Theory, CLT) | Decorative chrome, repeated icons, drop shadows on every card | Strip; one signal per meaning | Drop the icon if the label is enough |
| **Mental Model** | Kenneth CRAIK, *The Nature of Explanation* (1943) | Action name diverges from what the user expects | Rename to match the convention | "Delete" deletes; "Archive" archives; no euphemisms |
| **Jakob's Law** | Jakob NIELSEN (Nielsen Norman Group, NN/g) | Custom date picker, custom checkbox that behaves not-quite-natively | Use the native control or a faithful copy of the platform pattern | `<input type="date">`, `<input type="checkbox">`, plain `<nav>` |
| **Paradox of the Active User** | ROSSON & CARROLL, 1987 | Onboarding gated by a manual / multi-screen tutorial | Embed contextual tooltips and let users start immediately | `popover` attribute next to controls; "Show me how" link inline |

## 4. Time: what the user feels

| Law | Origin | Trigger | Action | Hook |
|---|---|---|---|---|
| **Doherty Threshold** | DOHERTY & THADANI, IBM Systems Journal, 1982 | UI response > 400 ms with no visible work | Bring under 400 ms **or** show progress (named-step bar, skeleton, optimistic update) | Skeleton tiles `animate-pulse bg-surface-secondary` for > 300 ms loads |
| **Flow** | CSÍKSZENTMIHÁLYI, 1975 | Critical task interrupted by modals, tooltips, upsells | Defer interruptions to natural breakpoints; match difficulty to skill | Save-then-prompt; honour `prefers-reduced-motion`; never modal mid-typing |
| **Goal-Gradient Effect** | Clark HULL, 1932 | Multi-step flow without progress; users abandon mid-way | Show a progress bar; bias the visible % high at the start | `<progress max="5" value="2">` with label "Step 2 of 5" |
| **Parkinson's Law** | C. N. PARKINSON, *The Economist* (1955) | Form lets the user spend unbounded time on one field | Default sensible values; cap free text where appropriate; autofill | `<input value="…sensible default…">` with helper "We picked this for you" |
| **Zeigarnik Effect** | Bluma ZEIGARNIK, 1927 | Draft or onboarding left half-done with no resume affordance | Persist draft state; surface a gentle "Resume" entry point | `localStorage` draft + dashboard tile "Continue setup (3 of 5)" |

## 5. Aesthetics & robustness

| Law | Origin | Trigger | Action | Hook |
|---|---|---|---|---|
| **Aesthetic-Usability Effect** | KUROSU & KASHIMURA, Hitachi, 1995 | Functionally correct UI that feels rough; users report bugs that aren't bugs | Add polish (consistent radii, focus rings, spacing rhythm) **and** keep usability testing; beauty can mask real bugs | Audit on the 8-pt grid; one radius scale; one focus token; behavioural observation in tests |
| **Von Restorff Effect** (isolation) | Hedwig von RESTORFF, 1933 | Multiple highlighted items on one screen | Keep exactly one item visually loud; demote the rest | `bg-brand-blue text-white` on the primary CTA; secondary stays ghost |
| **Peak-End Rule** | KAHNEMAN, FREDRICKSON, SCHREIBER, REDELMEIER, 1993 | First / last screens of a flow are the dullest | Invest design budget there; the middle can stay plain | Polished welcome + tasteful success state; bullet-list middle is fine |
| **Serial Position Effect** | Hermann EBBINGHAUS (primacy + recency) | Important option buried in the middle of a list | Move to first or last position | Pin "Cancel" first or last on a destructive menu, not row 4 of 7 |
| **Postel's Law** | Jon POSTEL, RFC 761, 1980 | Strict validation rejects whitespace, hyphens in phone numbers, mixed-case emails | Accept liberally, normalise server-side, emit conservatively | `<input pattern>` only for syntax; trim & lowercase in the handler |
| **Tesler's Law** (conservation of complexity) | Larry TESLER, Xerox PARC, mid-1980s | UI tries to hide complexity the domain itself carries (dates, taxes, time zones) | Pick *who* absorbs it (designer / developer / user) and own it | Show timezone next to every time; let the user override |

---

## A note on Postel's Law

The Wikipedia article on the
[Robustness Principle](https://en.wikipedia.org/wiki/Robustness_principle)
is required reading before applying this one. Postel's rule is the
heuristic that lets your form accept "+33 6 12 34 56 78", "0612345678",
and "06 12 34 56 78" interchangeably. It is also the heuristic that
Marshall ROSE (2001) and THOMSON & SCHINAZI (RFC 9413, 2023) blame
for entrenching bugs as de facto standards: "any implementation of
the protocol is required to replicate the aberrant behavior, or it is
not interoperable."

For UX the takeaway is narrower than for protocol design:

- **Accept liberally at the user-input boundary** (phone numbers,
  whitespace, capitalisation, accented characters, RTL marks).
- **Normalise conservatively before storage**.
- **Emit canonically** (a single, lower-cased, NFC-normalised value
  back to other systems).
- Do **not** propagate sloppy input forward as if it were valid; that
  is where Postel's law becomes Postel's trap.

## How to apply (in this skill)

1. Pick **one** law per screen, not five. The pre-ship review walks
   the five buckets above and asks "which one is the most expensive
   miss?"
2. The law informs **the smallest concrete change** that satisfies
   it. "Apply Miller's Law" is not an action; "chunk the IBAN field
   into four groups of four with a non-breaking space" is.
3. When two laws conflict, **time beats decision beats perception**.
   Doherty Threshold (response < 400 ms) trumps a tidier
   Hick-grouping that requires a server round-trip.
4. **Refuse weaponisation.** Any law applied to extract behaviour the
   user did not consent to is a dark pattern; see `anti-patterns.md` in
   `sprezzature-ui`.
   Goal-Gradient is fine for onboarding; **faked** Goal-Gradient
   (progress bar that lies about remaining work) is not.
5. **Treat the Aesthetic-Usability Effect as a warning, not a tactic.**
   NN/g
   ([MORAN & WHITENTON, 2024](https://www.nngroup.com/articles/aesthetic-usability-effect/))
   reports users in usability tests routinely fail to flag real bugs
   on aesthetically pleasing sites: "things that look better are
   believed to work better, even when they don't." Polish ships
   alongside behavioural observation; it does not substitute for it.

## Trigger phrases (so future-you knows when to open this file)

- "Apply Hick / Fitts / Miller / Jakob / Tesler / Peak-End to this screen"
- "Why does this form feel slow / busy / disorganised?"
- "Audit this UI for cognitive load"
- "Is this a dark pattern?" → cross-load `anti-patterns.md` and stop here
- "Can you reference the Laws of UX?"

## Pre-ship checklist (canonical-set version)

- [ ] Top-level chooser ≤ 7 items, or grouped (Hick).
- [ ] Every interactive target at least 44 × 44 px (Fitts).
- [ ] Long strings chunked 3–4 chars (Miller).
- [ ] One loud thing per screen (Von Restorff).
- [ ] First + last screen polished (Peak-End).
- [ ] Native controls used unless there is a reason not to (Jakob).
- [ ] Progress shown for any flow > 1 step (Goal-Gradient).
- [ ] State communicated in ≥ 2 channels (Selective Attention).
- [ ] Inputs accept liberally, validate conservatively (Postel).
- [ ] Response ≤ 400 ms or progress shown (Doherty).
- [ ] No invented progress, scarcity, or social proof.
- [ ] Contextual help inline; no manual gate before first task
      (Paradox of the Active User).
- [ ] Behavioural observation in usability tests, not "looks good"
      verbal feedback alone (Aesthetic-Usability Effect).

## See also

- `sprezzature-ux-laws` and `sprezzature-ux-laws-audit` (one handler, the
  package's `scripts/audit_laws_of_ux.py`): static auditor that flags the eight
  mechanically-detectable violations (Hick, Miller, Fitts, Jakob, Tesler,
  Aesthetic-Usability, Selective Attention, Choice Overload). The Doherty
  Threshold is **not** among them and cannot be: response time is not a fact
  about source. Use Lighthouse on a real device for that one.
- Companion skill **`sprezzature-ui`**: broader generation skill with its
  own `ux-psychology.md` (cognitive-step-ordered, overlapping with
  this set), `anti-patterns.md` (weaponised-principle refusal
  targets), `ergonomics-criteria.md` (eight criteria for an
  ergonomic audit), and `ui-guidelines/foundations/accessibility.md`
  (the accessibility floor on top of which these laws build).
- Companion skill **`sprezzature-accessibility`**: static accessibility lint
  that catches Selective-Attention violations from a different angle
  (color-only state, missing alt, unlabelled inputs).

## Further reading (cited)

- YABLONSKI, Jon. *Laws of UX: Using Psychology to Design Better
  Products and Services*, 2nd ed., O'Reilly Media (2024). Curated
  index at [lawsofux.com](https://lawsofux.com/). The 2nd edition
  adds Paradox of Choice, Complexity Bias, Flow and the Paradox of
  the Active User to the curated set, plus considerations on
  accessibility, personalization, and the human factor.
- MORAN, Kate & WHITENTON, Kathryn. ["The Aesthetic-Usability
  Effect"](https://www.nngroup.com/articles/aesthetic-usability-effect/),
  Nielsen Norman Group (Feb 3, 2024).
- Wikipedia. ["Robustness
  Principle"](https://en.wikipedia.org/wiki/Robustness_principle);
  includes ROSE (2001) and THOMSON & SCHINAZI (RFC 9413, 2023)
  critiques relevant to Postel's Law.
- YABLONSKI, Jon. ["Onboarding for Active
  Users"](https://lawsofux.com/articles/2024/onboarding-for-active-users/),
  lawsofux.com (2024). Concrete patterns (Slackbot, Notion templates,
  in-product tooltips); load this when the user asks for an
  onboarding flow that should not feel like a manual.
- YABLONSKI, Jon. ["Design Principles for Reducing Cognitive
  Load"](https://lawsofux.com/articles/2015/design-principles-for-reducing-cognitive-load/),
  lawsofux.com (2015).
- YABLONSKI, Jon. ["Designing with Occam's
  Razor"](https://lawsofux.com/articles/2017/designing-with-occams-razor/),
  lawsofux.com (2017).
- YABLONSKI, Jon. ["The Psychology of
  Design"](https://lawsofux.com/articles/2018/the-psychology-of-design/),
  lawsofux.com (2018).
- YABLONSKI, Jon. ["Familiar vs
  Novel"](https://lawsofux.com/articles/2024/familiar-vs-novel/),
  lawsofux.com (2024); a companion to Jakob's Law, on when novelty
  is appropriate instead of the familiar pattern.
