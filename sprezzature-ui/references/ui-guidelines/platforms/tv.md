# Platforms — TV / Large screen

## When to consult this file

- 10-foot-distance UI
- Remote-control navigation (D-pad)

## Defaults

- **Big type, generous spacing.** Body ≥ 22 px.
- **Focus is the primary indicator**: large rings or scale changes on focus.
- **D-pad only.** Up/Down/Left/Right + Enter. Plan focus order carefully.
- **No hover, no touch.**
- **Reserve safe action zone** (~5% inset from edges) so important UI isn't cropped by overscan.

## Patterns

- Horizontal carousels of large tiles.
- Highlighted focused tile uses `scale-105` + colored ring.
- Long-form text justified with very generous `leading-relaxed`.

## Checklist

- [ ] Body ≥ 22 px.
- [ ] D-pad logical focus order works.
- [ ] Visible focus is a major design element (not subtle).
- [ ] 5% safe inset from edges.
