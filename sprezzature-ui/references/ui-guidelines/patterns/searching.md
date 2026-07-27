# Patterns — Searching

## When to consult this file

- Page search, app-wide search, command palette
- Filtering a list

## Core principles

- **Instant results > submit-and-wait.** Debounce 150–250 ms and update as the user types.
- **Empty query state shows recent or suggested.** Don't show "no results" when the box is empty.
- **No results state is actionable.** "No matches for 'foo'. Try a different search."
- **Search keyboard shortcut**: `/` to focus on web apps; `⌘K` for command palettes.
- **Announce result count** in a live region for screen readers.

## Concrete rules

1. `<input type="search">`: gets the native clear button and `inputmode="search"`.
2. Debounce with `setTimeout` + `clearTimeout`, not lodash.
3. Render results in a real list with `aria-live="polite"` count.
4. **Match highlighting**: wrap matches in `<mark>`.
5. **Keyboard navigation**: Arrow Down / Up moves through results; Enter activates.

## Pattern

```html
<form role="search" class="relative">
  <label for="q" class="sr-only">Search</label>
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
       class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-label-tertiary" aria-hidden="true">
    <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.34-4.34"/>
  </svg>
  <input id="q" type="search" inputmode="search" placeholder="Search…" dir="auto"
         class="block w-full rounded-full border border-separator bg-surface-secondary py-2.5 ps-10 pe-4 text-[17px]
                focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30
                dark:bg-surface-secondary-dark">
</form>
<p id="count" class="sr-only" role="status" aria-live="polite"></p>
<ul id="results" class="mt-3 divide-y divide-separator/40"></ul>

<script type="module">
  const input = document.getElementById('q');
  const list  = document.getElementById('results');
  const count = document.getElementById('count');
  let t;
  input.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(async () => {
      const items = await search(input.value);
      list.innerHTML = items.map(i => `<li class="py-2">${i.label}</li>`).join('');
      count.textContent = `${items.length} results`;
    }, 200);
  });
</script>
```

## Checklist

- [ ] `<input type="search">`.
- [ ] Debounced fetch.
- [ ] Result count announced.
- [ ] Empty state shows suggestions, not "no results".
- [ ] Keyboard nav: `/` to focus, arrows to navigate, Enter to activate.
