# Ergonomic Criteria

Eight criteria for evaluating any UI. Use them when reviewing a page or component, before shipping, and when the user asks for an "ergonomic audit".

---

## 1. Guidance

How the interface advises, orients, informs, and leads the user.

### 1.1 Prompting

- Make available actions discoverable. Hint at what the user can do, even before they hover.
- Examples: visible affordances on cards, labels on icon-only buttons (`aria-label`), placeholder text that shows expected format, breadcrumbs, "Next" buttons that name the next step.
- Concrete: never expose a control whose action isn't predictable from its appearance.

### 1.2 Grouping and distinction

Organize related items so the user can scan structure at a glance.

- **By location**: related items are physically near each other; unrelated items are separated by whitespace or a separator line. Use `space-y-*` and `divide-y` rather than ad-hoc margins.
- **By format**: different categories of items use distinct visual treatments (color, weight, shape). The destructive button is red; the link is blue; the heading is heavier than the body. Format must be consistent across the app.

### 1.3 Immediate feedback

Every user action gets a visible response within 100 ms.

- Press feedback: `active:scale-[0.97]` on buttons.
- Form submission: button shows `aria-busy="true"` + a spinner.
- Saved state: toast or inline `Saved` indicator.
- Long-running: skeleton or progress bar (see `ui-guidelines/patterns/loading.md`).

### 1.4 Legibility

Body text is reliably readable.

- Body ≥ 16 px; line height 1.5–1.6; line length 45–75 characters.
- Contrast ≥ 4.5:1 for text, ≥ 3:1 for UI.
- Single super-family (Roboto / Roboto Serif / Roboto Mono); no more than ~6 sizes per page.
- Avoid all-caps for body; reserve for short labels with letter-spacing.

## 2. Workload

How much effort the interface costs the user: to read, to remember, to act.

### 2.1 Brevity

- **Conciseness**: short labels, no filler. "Send" beats "Send message now". "Continue" beats "Click here to continue".
- **Minimal actions**: a goal takes the fewest possible steps. Pre-fill what you know. Skip confirmations for reversible actions; replace them with an undo banner (see `ui-guidelines/patterns/undo-and-redo.md`).

### 2.2 Information density

Each screen carries exactly as much information as the user needs to make the next decision: no more, no less.

- Cut nice-to-have decoration that competes with content.
- Hide secondary actions behind a "More" menu when the primary action is clear.
- For complex forms, use progressive disclosure: show the next step only when the current is complete.

## 3. Explicit control

The user, not the system, is in charge.

### 3.1 Explicit actions

- The system acts only on a user gesture. Don't auto-submit a search filter on every keystroke without debouncing; don't auto-save a draft if "Save" is the user's mental model.
- Confirm destructive actions, but prefer undo over confirmation when undo is cheap (see `ui-guidelines/patterns/undo-and-redo.md`).

### 3.2 User control

- The user can stop, pause, resume, undo, abort.
- Long operations are cancellable.
- Forms can be reset.
- Modal dismissal is always possible (`Escape`, backdrop, close button).

## 4. Adaptability

The interface fits the user, not the other way around.

### 4.1 Flexibility

- Several ways to accomplish the same goal where reasonable (keyboard shortcut + button + menu item for "Save").
- Preferences are honored: `prefers-color-scheme`, `prefers-reduced-motion`, `prefers-reduced-data`, `prefers-contrast`, `prefers-reduced-transparency`, language, time zone.
- See `ui-guidelines/foundations/accessibility.md` and `dark-mode.md`.

### 4.2 Accounting for user experience

- Beginners get clear, slightly verbose guidance; experts can skip ahead.
- Power-user features (`⌘K`, keyboard shortcuts) are present but discoverable, not required.
- Onboarding is skippable (`ui-guidelines/patterns/onboarding.md`).

## 5. Error management

Errors are prevented, and when they happen, they're easy to recover from.

### 5.1 Protection against errors

- Input constraints stop bad input before it's submitted: `type="email"`, `required`, `min`/`max`, `pattern`.
- Disable buttons while submitting; re-enable on completion.
- Ask for confirmation on irreversible destructive actions.

### 5.2 Quality of error messages

- Supportive, not accusatory: "That doesn't look like an email address" beats "Invalid email format".
- Specific: name the field, name the issue, suggest a fix.
- Located next to the offending input via `aria-describedby`.
- Announced via `role="alert"` for screen readers.
- See `ui-guidelines/foundations/writing.md` for tone.

### 5.3 Error correction

- After an error, the user's prior input is preserved.
- Focus moves to the first offending field on submit failure.
- The correction takes one action, not a full restart.

## 6. Consistency

Same purpose, same look. Same look, same purpose.

- One alignment per region.
- One spacing scale, one type scale, one color token set across the app.
- A button looks like a button everywhere; a link looks like a link everywhere.
- Component layout, icon family, motion curves do not change between screens.
- The semantic Tailwind tokens in `stack-tailwind.md` are the source of truth.

## 7. Significance of codes and labels

The relation between a label and what it represents is obvious.

- Verb-first button labels: "Send message", not "Submit".
- Icons use canonical metaphors (`ui-guidelines/foundations/icons.md`): heart = favorite, gear = settings, magnifier = search.
- No internal jargon or product code names in user-facing copy.
- Status badges use words ("Sent", "Failed", "Draft") plus a color, never color alone.

## 8. Compatibility

The interface matches the user's mental model and external context.

- Conventions from the operating system and the web are respected: form fields support `autocomplete`; `<input type="search">` shows a clear button; back means back.
- The interface matches the user's task vocabulary, not the developer's.
- Locale, date format, currency, number format follow `Intl` (`ui-guidelines/foundations/inclusion.md`).
- Print, share, copy behave the way users expect.

---

## How to use this checklist

Before shipping any non-trivial UI, walk the eight criteria and mark each:

- [ ] **Guidance**: affordances are visible, items are grouped, feedback is immediate, text is legible.
- [ ] **Workload**: labels are short; goals take the fewest possible steps; no decorative noise.
- [ ] **Explicit control**: the user, not the system, initiates change; nothing is irreversible without undo.
- [ ] **Adaptability**: user preferences honored; multiple paths to common goals; onboarding is skippable.
- [ ] **Error management**: input is constrained; errors say what + why + what to try; prior input is preserved.
- [ ] **Consistency**: one alignment, one scale, one token set, one icon family.
- [ ] **Significance**: labels and icons match canonical meaning; no jargon.
- [ ] **Compatibility**: OS / web conventions honored; locale-aware; matches user vocabulary.

This complements `references/checklist.md` (technical pre-ship gate). The technical checklist asks "does it work?"; this one asks "is it usable?".
