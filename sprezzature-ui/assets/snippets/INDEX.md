# Snippets — one Law of UX per file

Copy-paste-friendly HTML fragments, one per mechanically-implementable
Law of UX. Each file is self-contained, follows the sprezzature-ui stack
rules (Tailwind utility classes, semantic HTML, dark-mode peers,
visible focus rings, 44 px hit areas, `prefers-reduced-motion`
honoured), and passes both the `sprezzature-ux-laws` static auditor and the
`sprezzature-accessibility` lint with zero findings.

The catalog is the make-side counterpart to
`sprezzature-ux-laws/scripts/audit_laws_of_ux.py`'s `--fix` mode: the
auditor repairs what the agent emits; this catalog gives the agent
shapes worth emitting in the first place.

| Snippet | Law | Trigger phrases |
|---|---|---|
| `miller-iban-input.html` | **Miller's Law** | "IBAN field", "credit-card input", "code input", "phone number input", "chunk this code" |
| `peak-end-success.html` | **Peak-End Rule** | "success screen", "thank-you page", "checkout complete", "final state", "celebration screen" |
| `goal-gradient-progress.html` | **Goal-Gradient Effect** | "progress bar", "checkout step", "multi-step form progress", "biased progress" |
| `doherty-skeleton.html` | **Doherty Threshold** | "loading state", "skeleton loader", "fetch placeholder", "while we load", "data is loading" |
| `von-restorff-cta.html` | **Von Restorff Effect** | "primary CTA", "hero buttons", "one loud button", "primary vs secondary actions" |
| `jakob-native-controls.html` | **Jakob's Law** | "form fields", "date input", "email input", "native controls", "signup form" |
| `chunking-settings.html` | **Chunking** | "settings page", "grouped settings", "account preferences", "section list" |
| `zeigarnik-resume.html` | **Zeigarnik Effect** | "resume onboarding", "continue setup", "dashboard tile", "pick up where you left off" |

## How to use

1. **At generation time.** The agent loads the relevant trigger phrase
   from this index, opens the named file, copies the body, adapts the
   strings to the user's domain. Each snippet already carries the
   required dark-mode peers and focus rings — do not strip them.
2. **At audit time.** Run the emitted page through
   `python sprezzature-ux-laws/scripts/audit_laws_of_ux.py <page>` and
   `python sprezzature-accessibility/scripts/lint_a11y.py <page>` to
   confirm the adaptation did not regress what the source guaranteed.
3. **As a refusal target.** When a user asks for a UI pattern that
   the catalog already names, refuse to invent a one-off — start
   from the snippet.

## Why these eight (and not all 30)

The full canonical Yablonski set is documented in
`sprezzature-ux-laws/references/laws-of-ux.md`. Of the 30 laws, only eight
have an HTML embodiment that can stand alone on a page: the rest
(Hick, Cognitive Load, Tesler, Postel, Aesthetic-Usability, Selective
Attention, …) are *meta*-laws that constrain *every* surface rather
than producing a discrete one. They live as audit rules + decision
hooks in the reference, not as snippets here.

## Adding a new snippet

1. Pick a law that has a self-contained HTML embodiment (think:
   could a junior dev copy-paste this into a fresh project and have
   it work?).
2. Write the snippet at `sprezzature-ui/assets/snippets/<law-slug>.html`.
3. Run **both** auditors against it — zero findings is the
   acceptance bar.
4. Add a row to this index with the law name and 2-4 trigger phrases.
5. Add a test in `tests/test_snippet_catalog.py` so the dual-auditor
   check runs in CI.
