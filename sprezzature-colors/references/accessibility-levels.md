# Accessibility levels for colour: design for the worst case, offer more

Should a figure (or any coloured interface) be built for the *worst* visual
condition, or should it ship several levels with a sensible default and stronger
options behind a switch? This note answers both from the literature and states
what this project does.

Acronyms used once and then reused: colour vision deficiency (CVD), Web Content
Accessibility Guidelines (WCAG), Colour Universal Design (CUD), Accessible
Perceptual Contrast Algorithm (APCA).

## The short answer

Both, layered.

1. The **default** is designed for the worst case, but the worst case is *no
   colour perception at all*, and you reach it through **method, not palette**:
   never let colour be the only cue, keep marks separable by lightness, and hold
   a real contrast ratio. A design that survives greyscale survives every CVD.
2. **Extra levels** sit on top for people who want them: a higher-contrast tier,
   palettes tuned to one deficiency, a print or monochrome variant. They are
   enhancements, never a replacement for a default that is already accessible.

This mirrors the tiered thinking WCAG itself uses, and it matches the
interactivity `mode` argument used elsewhere in this repo: one good default,
other levels available.

## What the literature says

**WCAG 1.4.1 "Use of Color" (Level A) is the floor.** Colour must never be the
only visual means of conveying information. The stated intent is that the
information still reaches users who "cannot see color" and people on "monochrome
displays". In practice this means redundancy: pair every colour with a second
channel such as a text label, an icon, a shape, a pattern, or position. This is
a Level A criterion, so it is the minimum, not the aspiration.

**The deficiencies are not equally common, and there is no palette that suits
all of them at once.** Red-green deficiencies (deuteranopia and protanopia) are
by far the most common, around 1 in 12 men. Blue-yellow (tritanopia) is rare.
Total colour blindness (achromatopsia, true greyscale vision) is rarest, about 1
in 30,000. The research is blunt about the consequence: there is no
one-size-fits-all colour-only solution, and a palette tuned to help one
deficiency can collapse another. What travels across all of them is the method,
redundancy and contrast, not any specific set of hues.

**Greyscale is the universal worst case.** Achromatopsia is the only condition
that truly sees in shades of grey, and the useful property follows directly: if
a design reads correctly in greyscale, it reads correctly under every milder
deficiency too. So "design for the worst case" is best operationalised as
"design so it survives greyscale", which is exactly the redundancy-plus-luminance
rule above. Testing the greyscale render is therefore the single most
informative check.

**A validated universal palette exists: Okabe-Ito / Colour Universal Design.**
Okabe and Ito published an eight-colour set in 2002 that was chosen empirically
rather than by formula. The colours differ in brightness and saturation and stay
out of the yellow-green range where CVD confusion is worst, and the set was
verified against colour-blind vision. It is the most cited colourblind-safe
palette for scientific figures. It is a strong default, not a cure: it still
needs redundant cues, because two of its colours can still converge for a given
viewer.

**Contrast has explicit levels, and a graded future.** WCAG 2.x already tiers
contrast: AA asks for 4.5:1 for normal text (3:1 for large text and for
graphical objects), AAA asks for 7:1. WCAG 3.0 (the "Silver" draft) replaces the
binary pass/fail with a graded 0-to-4 score (Fair, Good, Excellent) and is
trialling APCA, a perceptual model that reports a lightness-contrast value and
accounts for font size, weight, and which colour is on top. As of 2026, WCAG 2.x
AA remains the legal baseline, and APCA is the better design compass for
readability. The takeaway for us is that "accessible" is already a spectrum with
named rungs, so shipping levels is aligned with where the standards are going.

## The layered model to adopt

**Level 0: Default (everyone, no opt-in).** Universal design.
- No colour-only encoding. Every category or state also carries a label,
  position, shape, or pattern.
- Marks are separable by lightness, so signed or diverging data uses a
  blue-to-red split (which survives red-green blindness) rather than red-green.
- Text and essential marks meet WCAG 2.x AA contrast.
- Categorical hues come from a CUD-style palette (Okabe-Ito or the house
  Apple-derived set filtered the same way).
- Verified to survive the three CVD simulations and, above all, greyscale.

**Optional levels (available, never required).**
- **High-contrast / AAA.** Push text and marks to 7:1 (or the APCA equivalent)
  for low-vision users and hostile lighting.
- **Deficiency-tuned palettes.** A deuteranopia, protanopia, or tritanopia
  variant that maximises separation for that specific viewer, offered as a
  choice because no single palette is optimal for all three.
- **Monochrome / print.** A no-colour variant that leans entirely on lightness,
  pattern, and labels, for greyscale printing and e-ink.

The default already assumes the person who cannot rely on colour. The optional
levels let a user who knows their own need turn the dial further, the same way
operating systems and games ship colour-blind modes on top of an interface that
is already usable without them.

## What this project does (and where it grows)

**The default is implemented.** Across `sprezzature-figures`, categories are told apart
by shape, direct labels, and position as well as hue; diverging data uses the
blue-to-red house convention; text and marks target WCAG AA. Every figure is
checked with `sprezzature-colors/scripts/simulate_cvd.py` (the three deficiencies plus
`--grayscale`) and with `sprezzature-accessibility/scripts/lint_a11y.py`, and the
result is looked at through the Ralph Eyeball Loop, including the CVD and
greyscale sheets. In other words, the shipped default is designed against the
greyscale worst case by method, which is what the literature recommends.

**The optional levels are the roadmap.** The clean way to expose them is the
pattern already used for interactivity: an argument with a universal default and
opt-in alternatives, for example an `accessibility` or `palette` switch offering
`universal` (default), `deuteranopia`, `protanopia`, `tritanopia`,
`high-contrast`, and `monochrome`. `sprezzature-colors` already holds the pieces this
needs, the CVD matrices in `simulate_cvd.py` and the OKLCH lighten/darken and
contrast audit in `audit_contrast.py`, so the levels can be generated and
verified from one source rather than hand-maintained.

## Automatic from the operating system, or a simulation for review

Two questions hide behind "adapt to accessibility", and only one has an automatic
answer.

The operating system exposes a few preferences a page can honour without asking:
`prefers-contrast`, `forced-colors`, and `prefers-color-scheme`. A figure can carry
those variants in its own stylesheet and switch to them on its own, which is where the
`high-contrast` level belongs. The operating system exposes nothing about colour vision
deficiency: it does not know, and should not, that a reader is a deuteranope, because
that reader already sees the page through their own eyes. So a per-deficiency level can
never be selected automatically. It stays a generator output for whoever asks, plus a
review tool, never something the page guesses.

That review tool is the gallery's "See it for… / Voir pour…" control. It applies the
same Machado matrices as `simulate_cvd.py`, live, as a Scalable Vector Graphics (SVG)
`feColorMatrix` filter over the *default* figures, so a sighted reader can see a figure
the way a colour-blind reader does. The point it makes is that the default holds up. It
simulates, it does not replace, and colour blindness never becomes a mode a reader has
to pick.

## Practical checklist

- Never encode meaning by colour alone. Add a label, shape, position, or
  pattern.
- Prefer blue-to-red for signed data. Avoid red-green pairings.
- Meet WCAG AA contrast by default; offer AAA / high-contrast as a level.
- Start from a CUD-style palette; do not tune the default for a single
  deficiency.
- Test the **greyscale** render first. If it reads there, it reads for everyone.
- Offer stronger and deficiency-specific levels as options, never as the price of
  entry.

## Sources

- [Understanding WCAG Success Criterion 1.4.1: Use of Color (W3C)](https://www.w3.org/TR/UNDERSTANDING-WCAG20/visual-audio-contrast-without-color.html)
- [Types of Colour Blindness: Colour Blind Awareness](https://www.colourblindawareness.org/colour-blindness/types-of-colour-blindness/)
- [Color Universal Design (Okabe & Ito)](https://jfly.uni-koeln.de/color/) and [Colorblind-Safe Palettes for Science Figures](https://sci-draw.com/blog/colorblind-safe-palettes-okabe-ito-reference)
- [Designing for Color Blindness: greyscale covers every deficiency](https://colorblind.io/guides/designing-for-color-blindness)
- [APCA in a Nutshell](https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html) and [WCAG 3.0 tiers, APCA, and what is changing](https://designproject.io/blog/web-accessibility-wcag-apca/)
