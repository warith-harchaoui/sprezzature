# Components — Sliders

## When to consult this file

- A continuous numeric value (volume, brightness, range)
- Coarse adjustment where a numeric input would be tedious

## Core principles

- **For numbers users adjust by feel**, not precise typed values.
- **Pair with a visible value** so users see what they're setting.
- **Min/max labels** at the ends, or a tick at meaningful values.

## Concrete rules

1. Use `<input type="range">`: native, keyboard-arrow accessible.
2. Style the track and thumb via WebKit / Mozilla pseudo-elements; keep the thumb ≥ 28 px diameter for touch.
3. Show current value next to the slider (e.g. `<output>`).
4. Tabular numerals for the value.

## Pattern

```html
<label class="block">
  <span class="block text-[15px] font-medium">Volume</span>
  <div class="mt-2 flex items-center gap-3">
    <input type="range" id="vol" min="0" max="100" value="60"
           class="flex-1 accent-brand-blue">
    <output for="vol" class="w-10 text-right text-[15px] tabular-nums text-label-secondary dark:text-label-secondary-dark">60</output>
  </div>
</label>
<script type="module">
  const vol = document.getElementById('vol');
  vol.addEventListener('input', () => vol.nextElementSibling.value = vol.value);
</script>
```

## Checklist

- [ ] `<input type="range">`.
- [ ] Value visible next to the slider.
- [ ] Arrow keys / Page Up/Down work.
- [ ] Thumb ≥ 28 px touch target.
