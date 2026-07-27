# Patterns — Feedback

## When to consult this file

- After any user action (success, failure, pending)
- Surfacing system state to the user

## Core principles

- **Confirm visibly, dismiss quietly.** Success toasts auto-dismiss; errors persist.
- **Feedback fits the gravity.** Inline success ≤ banner ≤ alert.
- **Don't tear the user away from their task** to show feedback unless absolutely needed.
- **Errors are supportive, not accusatory.** "We couldn't find that account" beats "Invalid email".

## Surfaces

| Outcome | Surface | Duration |
|---|---|---|
| Tiny success (saved, copied) | Toast / inline status | 2–4 s |
| Mild error (validation) | Inline below the field | Persist until corrected |
| Critical error (network down) | Banner at top of view | Persist until resolved |
| Blocking error (data corruption) | Alert dialog | Persist until acknowledged |

## Concrete rules

1. Use a single live region (`role="status" aria-live="polite"`) for transient announcements.
2. Errors are announced `assertive`; everything else `polite`.
3. Toasts: bottom on mobile, top-right on desktop. Auto-dismiss ≥ 2 s; never < 1.5 s.
4. Don't stack more than 3 toasts; collapse to "+N more".

## Pattern — toast

```html
<div id="toast" role="status" aria-live="polite"
     class="pointer-events-none fixed inset-x-0 bottom-6 z-40 mx-auto flex max-w-sm justify-center px-4">
  <div class="pointer-events-auto rounded-full bg-label-primary px-4 py-2 text-[15px] font-medium text-surface-primary opacity-0 transition-opacity duration-200 dark:bg-label-primary-dark dark:text-surface-primary-dark">
    Saved
  </div>
</div>
```

## Checklist

- [ ] Success quiet, error persistent.
- [ ] Live region announces state changes.
- [ ] Supportive error copy.
- [ ] Auto-dismiss only for non-actionable success.
