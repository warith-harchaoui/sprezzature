# Components — Alerts

## When to consult this file

- Confirming a destructive action
- Surfacing a critical, blocking error
- Asking the user to acknowledge something important

## Core principles

- **Use alerts sparingly.** Each one interrupts. Reserve for actions the user cannot undo or messages they must not miss.
- **Title, body, action.** One short title (≤ 8 words), one or two sentences of body, one or two buttons.
- **Two buttons max.** Cancel + confirm. More than two indicates the wrong component (use a sheet).
- **Primary action on the right (end)** in LTR. Destructive primary uses red text or a red filled button.
- **No icon, no decoration.** Alerts are textual.

## Concrete rules

1. **Use the native `<dialog>`** with `.showModal()`: focus trap and Escape are free.
2. **Center on screen** (not bottom). Bottom = sheet, top = banner.
3. **Backdrop dismissible** to "cancel": click outside closes with the cancel value.
4. **No scroll inside.** If the body is too long, you don't need an alert.
5. **Announce on open** for screen readers (most ATs read `<dialog>` open events; verify with VoiceOver / NVDA).

## Pattern

```html
<dialog id="alert" class="m-auto w-full max-w-sm rounded-2xl bg-surface-primary p-5 text-center backdrop:bg-black/40 dark:bg-surface-primary-dark">
  <h2 class="text-[17px] font-semibold">Delete this project?</h2>
  <p class="mt-1 text-[15px] text-label-secondary dark:text-label-secondary-dark">This action can't be undone.</p>
  <div class="mt-5 flex gap-2">
    <button value="cancel" class="flex-1 min-h-11 rounded-xl bg-surface-secondary px-4 font-medium dark:bg-surface-secondary-dark">Cancel</button>
    <button value="confirm" class="flex-1 min-h-11 rounded-xl bg-brand-red px-4 font-semibold text-white">Delete</button>
  </div>
</dialog>
<script type="module">
  const dlg = document.getElementById('alert');
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close('cancel'); });
</script>
```

## Checklist

- [ ] Title ≤ 8 words, sentence case.
- [ ] One or two buttons; primary on the end.
- [ ] Destructive named the consequence.
- [ ] Backdrop click closes as cancel.
- [ ] `Escape` closes.
- [ ] No long-form body or scroll inside.
