# Foundations — Writing


## When to consult this file

- Any visible string: button label, alert body, empty state, error message, onboarding step

## Core principles

- Be concise, clear, and helpful, in that order.
- Use the user's language, not the developer's: "Free up space" beats "Purge cache."
- Verbs in buttons: "Continue", "Send", "Delete photo"; never "OK" for a consequential action.
- Sentence case everywhere except brand names and acronyms. Title Case feels dated.
- Don't apologize, don't blame: "We couldn't find that account", not "Error 401: invalid credentials".
- Plain language, around grade-8 reading level. Avoid jargon, idioms, internal product names.
- Numbers as numerals in UI ("3 items"); spell them out only when starting a sentence in long prose.

## Concrete rules

1. **Button labels**: 1–3 words, verb-first. "Save changes" not "Save".
2. **Destructive buttons**: name the consequence. "Delete account" not "Yes".
3. **Empty states**: tell the user what to do next. "No projects yet. Create one to get started."
4. **Error messages**: explain what happened, why, and what to try.
5. **Loading messages**: only if > 5 s expected. "Crunching numbers…" beats nothing.
6. **Onboarding**: one idea per screen, max 8 words in the headline.
7. **Punctuation**: no periods on UI labels under ~6 words. Periods on full sentences.
8. **Capitalization**: sentence case for buttons, menu items, list items, headers (unless titles of works).
9. **Avoid "please".** It softens UI to the point of feeling weak. "Try again" beats "Please try again".
10. **Use contractions** ("you're", "we'll") for warmth.

## Voice traits to favor

| Do | Don't |
|---|---|
| Direct | Hedging |
| Warm | Robotic |
| Specific | Vague |
| Active voice | Passive voice |
| Short sentences | Compound clauses |
| Real verbs | Buzzwords |

## Quick rewrites

| Before | After |
|---|---|
| "Error: invalid email format" | "That doesn't look like an email address" |
| "Are you sure you want to proceed?" | "Delete this draft?" |
| "Submit" | "Send message" |
| "An unexpected error occurred" | "Something went wrong. Try again?" |
| "Please enter your password" | "Enter your password" |
| "Loading…" | "Looking up your account…" |
| "No data" | "No results yet. Try a different search." |

## Checklist

- [ ] Every button label starts with a verb (or is a single object noun if context is clear).
- [ ] Sentence case throughout.
- [ ] No "please". No "OK" on consequential actions.
- [ ] Empty states give a next step.
- [ ] Errors say what + why + what to try.
- [ ] No internal jargon or product code names.
