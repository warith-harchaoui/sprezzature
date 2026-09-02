# UX Psychology: triggers and actions

Rules-only. Each principle is one line: **trigger → action**. Background and worked examples have been removed; Claude already knows the underlying cognitive science. This file exists so the skill can *act* on it.

Organised by the cognitive step a user is in.

> **Canonical Laws of UX live in the `sprezzature-ux-laws` skill.** When
> the user names one of Jon Yablonski's 30 laws explicitly (Hick,
> Fitts, Miller, Jakob, Tesler, Doherty, Peak-End, Postel, Paradox
> of the Active User, …), load
> `sprezzature-ux-laws/references/laws-of-ux.md` instead: it gives the
> trigger / action / Tailwind hook for each law and the static
> auditor counterpart at
> `sprezzature-ux-laws/scripts/audit_laws_of_ux.py`. The two files
> deliberately overlap; this one is broader (Anchoring, Reciprocity,
> Endowment, Default Bias, Banner Blindness, Curse of Knowledge, …),
> the canonical file is more concrete on Tailwind hooks for the
> named-by-the-user set.

## 1. Information: what the user lets in

| Principle | Trigger | Action |
|---|---|---|
| Hick's Law | Choice among > 7 items | Group or hide behind a "More" toggle |
| Cognitive Load | Decorative chrome, redundant icons | Strip; one signal per meaning |
| Anchoring | Three-option chooser (plans, pricing) | Centre the option you want chosen |
| Fitts's Law | Primary action far from current cursor / thumb | Enlarge it; on mobile, bottom-anchor |
| Progressive Disclosure | Settings form > 6 fields | Collapse advanced; reveal on demand |
| Visual Hierarchy | Tested in grayscale and hierarchy collapses | Reset with weight + size, not colour |
| Von Restorff | Multiple highlighted items on one screen | Reduce to one |
| Aesthetic-Usability | Functional but unpolished | Add polish without sacrificing clarity |
| Banner Blindness | Content styled like an ad strip | Restyle as content, not promo |
| Fitts corollary (edges) | High-frequency desktop action mid-screen | Move to a screen edge or corner |

## 2. Meaning: what the user fills in

| Principle | Trigger | Action |
|---|---|---|
| Mental Model | Action name diverges from convention | Rename to match (Save = save, Delete = delete) |
| Familiarity Bias | Custom control where a native one exists | Use the native control |
| Social Proof | Generic logo wall | Replace with named customers + numbers |
| Scarcity | "Only N left" claim | Only ship if true; never fake |
| Reciprocity | Email gate before product shown | Show product first |
| Goal Gradient | Multi-step flow without progress | Show a bar; bias the visible % high |
| Authority & Halo | Trust signal placed at the end | Move to first viewport |
| Curse of Knowledge | Copy uses internal jargon | Test with someone outside the team |
| Aha! Moment | > 3 steps before value is visible | Cut intermediate steps |
| Occam's Razor | Flow feels confusing | Look for the obvious mistake first |
| Curiosity Gap | Clickbait language in copy | Drop it; reserve for content discovery |

## 3. Time: the user is in a hurry

| Principle | Trigger | Action |
|---|---|---|
| Loss Aversion | Choice framed as gain only | Reframe one side as loss; do not stack |
| Default Bias | Pre-ticked marketing consent | Untick it; pre-tick safe defaults only |
| Sunk Cost | Wizard forces restart on error | Persist progress; resume mid-flow |
| Reactance | "Email required" with no reason | Say why ("to send the receipt") |
| Decision Fatigue | Many trivial choices early in a flow | Eliminate, default, or defer |
| Hyperbolic Discounting | Asks for commitment before value | Show value, then ask |
| Labor Illusion | Long operation with no feedback | Show a named-step progress bar; do not fake |
| Tesler's Law | Trying to remove all complexity from the UI | Pick who absorbs it; do not hide it from both |
| Discoverability | Feature only accessible via deep menu | Surface in nav or onboarding |
| Investment Loops | Reset destroys saved customisation | Persist on logout / device change |

## 4. Memory: what the user takes away

| Principle | Trigger | Action |
|---|---|---|
| Peak-End | First / last screen of a flow is dull | Invest there; middle can stay plain |
| Zeigarnik | Draft left unfinished | Surface it as a gentle reminder, not a nag |
| Endowment | Customisation feels disposable | Persist; reuse across sessions |
| Chunking | List of > 7 unstructured items | Group into 3–4 chunks with labels |
| Recognition over Recall | Free-text input where options exist | Offer autocomplete / picker |
| Picture Superiority | Long text-only explanation | Add a diagram or annotated screenshot |
| Storytelling | Release notes are bullet lists of "what" | Add a "why" line |
| Serial Position | Important option buried in the middle | Move to top or bottom |
| Delighters | Success moment is silent | Add one tasteful confirmation; do not overdo |
| Exit Points | Pushy retention at the door | Drop it; let the user leave clean |

## How to apply

- Pick one principle per task, not a dozen.
- Match to the cognitive step:
  - Landing → Hierarchy, Anchoring, Aesthetic-Usability, Banner Blindness.
  - Decision → Hick, Default Bias, Loss Aversion, Social Proof.
  - Long flow → Goal Gradient, Sunk Cost, Labor Illusion, Progressive Disclosure.
  - End → Peak-End, Endowment, Delighters, Exit Points.
- Refuse weaponisation. The dark-pattern list lives in `anti-patterns.md`. If a principle here would only work by manipulating the user, skip it.

## Pre-ship checklist

- [ ] One clear next action per screen.
- [ ] Hierarchy works in grayscale.
- [ ] Defaults are the safe, kind choice.
- [ ] First and last steps polished.
- [ ] Progress shown for any multi-step flow.
- [ ] Recognition beats recall in choosers.
- [ ] No invented social proof or scarcity.
- [ ] Clean exit at every reasonable point.
