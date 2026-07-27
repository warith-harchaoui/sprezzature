# Patterns — Drag and Drop

## When to consult this file

- Re-ordering a list
- Moving items between lists or columns (kanban)
- Uploading files via drop

## Core principles

- **Drag is a power user shortcut.** Provide a non-drag fallback (a "Move…" menu, or up/down buttons).
- **Show clear hit zones.** Highlight the target while dragging.
- **Live-announce** dragstart / drop for screen readers.
- **Keyboard parity.** Arrow keys must reorder when a drag handle is focused.

## Concrete rules

1. Use the native HTML Drag & Drop API with `draggable="true"`.
2. **Drag handle** visible on each item (`⠿` grip icon); only the handle initiates drag.
3. **Drop zone styling**: ring or background tint on `dragover`.
4. **Cancel** support: Escape returns the item to its origin.
5. **File drop** uses `<input type="file">` for fallback + drag listeners on the surface.

## Pattern — file drop

```html
<label for="file" class="block">
  <span class="sr-only">Upload a file</span>
  <div id="drop" class="grid place-items-center rounded-2xl border-2 border-dashed border-separator p-8 text-center transition-colors hover:border-brand-blue">
    <p class="text-[15px] text-label-secondary dark:text-label-secondary-dark">Drag a file here, or <span class="text-brand-blue underline">choose one</span>.</p>
    <input id="file" type="file" class="sr-only">
  </div>
</label>

<script type="module">
  const drop = document.getElementById('drop');
  ['dragenter','dragover'].forEach(e => drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add('border-brand-blue','bg-brand-blue/5'); }));
  ['dragleave','drop'].forEach(e => drop.addEventListener(e, () => drop.classList.remove('border-brand-blue','bg-brand-blue/5')));
  drop.addEventListener('drop', (ev) => {
    ev.preventDefault();
    const file = ev.dataTransfer.files?.[0];
    if (file) handleFile(file);
  });
</script>
```

## Checklist

- [ ] Non-drag fallback present.
- [ ] Drop zones highlight on `dragover`.
- [ ] Escape cancels.
- [ ] Keyboard reorder via arrow keys when handle focused.
- [ ] Announced via live region.
