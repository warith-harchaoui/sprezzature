# Components — Lists and Tables

## When to consult this file

- A vertical list of items (settings, contacts, files)
- A data grid with columns
- A feed of homogeneous cards

## Core principles

- **Lists for sequential or homogeneous items**; tables for comparable columns of data.
- **Use real `<ul>` / `<ol>` / `<table>`** — they carry semantic count info for screen readers.
- **Separator between rows**, not card chrome around each. (Card-per-row only when rows are content-rich blocks.)
- **Sticky headers** on tables.
- **Tabular numerals** in numeric columns.

## List patterns

```html
<ul class="divide-y divide-separator/40">
  <li class="flex min-h-11 items-center gap-3 px-4 py-3">
    <img src="/u/a.jpg" alt="" class="h-9 w-9 rounded-full bg-surface-secondary object-cover">
    <div class="flex-1">
      <p class="text-[17px]">Sara Khouri</p>
      <p class="text-[13px] text-label-secondary dark:text-label-secondary-dark">sara@example.com</p>
    </div>
    <button class="text-brand-blue text-[15px] font-medium">Invite</button>
  </li>
</ul>
```

## Table patterns

```html
<table class="w-full text-left text-[15px]">
  <thead class="sticky top-0 bg-surface-primary/80 backdrop-blur dark:bg-surface-primary-dark/80">
    <tr class="border-b border-separator/40 text-[13px] uppercase tracking-wider text-label-secondary">
      <th scope="col" class="px-4 py-2 font-medium">Name</th>
      <th scope="col" class="px-4 py-2 font-medium text-right">Size</th>
      <th scope="col" class="px-4 py-2 font-medium text-right">Modified</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-separator/40">
    <tr>
      <th scope="row" class="px-4 py-3 font-normal">report.pdf</th>
      <td class="px-4 py-3 text-right tabular-nums">1.2 MB</td>
      <td class="px-4 py-3 text-right text-label-secondary dark:text-label-secondary-dark">2 h ago</td>
    </tr>
  </tbody>
</table>
```

## Concrete rules

1. **Min row height 44 px** for tappable rows.
2. **Chevron at row end** if tapping the row drills into detail (rotate in RTL).
3. **Selection**: checkbox on the start; entire row clickable.
4. **Empty state**: show what action to take, not a blank list.
5. **Virtualize lists > 200 items** to keep scroll smooth.

## Checklist

- [ ] Semantic `<ul>` / `<ol>` / `<table>`.
- [ ] Separators between rows.
- [ ] Sticky table header.
- [ ] Tabular numerals on numeric columns.
- [ ] Empty state present.
