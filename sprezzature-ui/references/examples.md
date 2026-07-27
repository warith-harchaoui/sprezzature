# Worked examples — copy-and-adapt shapes

Two end-to-end shapes that show the hard rules applied together (semantic
HTML, Tailwind tokens, dark-mode peers, focus rings, reduced-motion guards).
For the generic per-surface primaries see `assets/components/*.html`; for the
law-keyed catalog see `assets/snippets/INDEX.md`.

## Example 1 — primary CTA button

User: "Give me a primary button labeled 'Get started'."

```html
<button class="inline-flex min-h-11 items-center justify-center gap-2 rounded-full
               bg-brand-blue px-5 py-3 text-[17px] font-semibold text-white
               transition-transform duration-100 ease-out
               hover:opacity-90 active:scale-[0.97]
               focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue
               focus-visible:ring-offset-2 focus-visible:ring-offset-surface-primary
               motion-reduce:active:scale-100
               disabled:opacity-50 disabled:pointer-events-none">
  Get started
</button>
```

## Example 2 — confirm dialog (destructive)

```html
<button id="open-del" class="text-brand-red">Delete project</button>

<dialog id="del" class="w-full max-w-sm rounded-2xl bg-surface-primary p-5 text-center
                         backdrop:bg-black/40 dark:bg-surface-primary-dark">
  <h2 class="text-[17px] font-semibold text-label-primary dark:text-label-primary-dark">
    Delete this project?
  </h2>
  <p class="mt-1 text-[15px] text-label-secondary dark:text-label-secondary-dark">
    This action can't be undone.
  </p>
  <div class="mt-5 flex gap-2">
    <button value="cancel" class="flex-1 min-h-11 rounded-xl bg-surface-secondary px-4 font-medium text-label-primary dark:bg-surface-secondary-dark dark:text-label-primary-dark">Cancel</button>
    <button value="delete" class="flex-1 min-h-11 rounded-xl bg-brand-red px-4 font-semibold text-white">Delete</button>
  </div>
</dialog>

<script type="module">
  const dlg = document.getElementById('del');
  document.getElementById('open-del').addEventListener('click', () => dlg.showModal());
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close('cancel'); });
  dlg.addEventListener('close', () => {
    if (dlg.returnValue === 'delete') { /* perform deletion */ }
  });
</script>
```
