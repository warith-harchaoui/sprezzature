# Publication-quality figure presets

`make_figure.py --preset <name>` swaps the house style for one of a
handful of journal-ready templates. Each preset locks font sizes,
figure width, and DPI to what the venue expects.

Sources: [Nature figure guide](https://www.nature.com/nature/for-authors/formatting-guide),
[Science figure prep](https://www.science.org/content/page/instructions-preparing-initial-manuscript),
[PLOS figure guidelines](https://journals.plos.org/plosone/s/figures),
[IEEE graphics preparation](https://www.ieee.org/publications/authors/author-tools.html).

## Available presets

| Preset | Width | DPI | Font | Notes |
|---|---|---|---|---|
| `publication` (default) | 3.5 in (single column) | 300 | Roboto Serif 8 pt labels / 10 pt title | Generic journal-safe; the fallback. |
| `nature-single` | 89 mm (~3.5 in) | 300 | Sans 5-7 pt labels | Nature single-column figure. Line weight 0.5-1 pt. |
| `nature-double` | 183 mm (~7.2 in) | 300 | Sans 5-7 pt labels | Nature double-column figure. |
| `science-single` | 55 mm (~2.17 in) | 300 | Sans 6 pt labels | Science narrow figure. |
| `science-double` | 120 mm (~4.72 in) | 300 | Sans 6 pt labels | Science wide figure. |
| `plos` | 7.5 in max | 300 | Sans-serif 8-12 pt labels | PLOS ONE / Biology; wide latitude on width. |
| `ieee-single` | 3.5 in | 300 | Times / Roboto Serif 8 pt | IEEE Transactions single-column. |
| `ieee-double` | 7.16 in | 300 | Times / Roboto Serif 8 pt | IEEE Transactions double-column. |
| `slide-16-9` | 13.33 in @ 96 dpi | 96 | Roboto 24 pt | Slide-deck figure. Not for print. |
| `web-hero` | 12 in @ 144 dpi | 144 | Roboto 14 pt | Blog / landing-page hero chart. Not for print. |

## What each preset enforces

- **Fonts.** Every text element uses the preset's font. Publication
  presets prefer Roboto Serif for labels (matches editorial body copy);
  slide / web presets use Roboto sans.
- **DPI.** 300 for print venues, 144 for retina web, 96 for slide
  decks. `make_figure.py --emit png` respects the preset's DPI.
- **Width.** Physical width in inches / millimetres, honoring the
  venue's single-column vs double-column figure grid.
- **Line weights.** 0.5-1 pt for print (readable at journal scale);
  1-2 pt for slides / web.
- **Marker sizes.** Scaled so a scatter with ~500 points reads at
  print size without overplotting a full black rectangle.
- **Color mode.** All presets are CVD-safe; publication presets add a
  parallel monochrome pass via `--emit svg` + `--mono` for grayscale
  reproduction.
- **Chartjunk stripped.** No backgrounds, no shadows, no gradients.
  The auditor is happy.

## Recipes

### Nature single-column figure with a colorblind-safe palette

```bash
python sprezzature-figures/scripts/make_figure.py data.csv \
    --x time --y response_ms \
    --kind line \
    --preset nature-single \
    --polarity lower-better \
    --emit svg --out fig1a.svg
```

### Slide-deck hero chart

```bash
python sprezzature-figures/scripts/make_figure.py revenue.csv \
    --x quarter --y revenue \
    --kind bar \
    --preset slide-16-9 \
    --polarity higher-better \
    --emit png --out slide-hero.png
```

### IEEE double-column with matplotlib backend

```bash
python sprezzature-figures/scripts/make_figure.py results.csv \
    --x epoch --y loss \
    --kind line \
    --preset ieee-double \
    --engine matplotlib \
    --emit png --out fig3.png
```

## Custom presets

Drop a YAML file at `<project>/sprezzature-figures.presets.yaml`:

```yaml
my-thesis:
  width_in: 5.5
  dpi: 600
  font_family: "Roboto Serif"
  font_size_label: 9
  font_size_title: 11
  line_weight: 0.7
  strip_chartjunk: true
  mono: false
```

`make_figure.py --preset my-thesis` picks it up automatically.
