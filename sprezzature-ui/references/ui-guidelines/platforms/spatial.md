# Platforms — Spatial / XR

## When to consult this file

- WebXR experiences
- 2D web content viewed in a spatial browser

## Defaults

- **Float content at comfortable depth** (≈ 1 m). Avoid placing UI at the eyes' near point.
- **Glassy, translucent surfaces** integrate with the user's environment.
- **Larger targets** (touch + gaze imprecise): ≥ 60 × 60 px in the rendered scene.
- **Subtle motion only**; sudden translations cause discomfort.
- **No fixed-position chrome** that follows the head; anchor UI in the scene.

## Patterns

- Cards with `bg-surface-primary/40 backdrop-blur-thick` to read on any background.
- Pinch / tap mapped through native gestures; no custom finger tracking unless required.
- 2D fallback always shipped for users without supported hardware.

## Checklist

- [ ] Targets ≥ 60 × 60 px in scene.
- [ ] Translucent surfaces with strong blur.
- [ ] No sudden camera moves.
- [ ] 2D fallback present.
