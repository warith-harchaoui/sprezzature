# Eleven films, eleven shapes

Written 2026-10-27, after watching the first set back. Two things were wrong
with it and they had the same cause.

**Every film ran the same eight beats** — claim, chips, panel, panel, claim,
panel, claim, outro — because they were written in one sitting from one
template. Watch two in a row and you have seen the format; watch four and the
suite looks like a slide deck with a voice over it.

**The French was a lookup table** keyed on the English strings, so each
fragment was translated alone, out of its sentence. That is how you get
*transformé en quelque chose qui tourne* and, in one caption, the *passé
simple*. The French is composed now, next to the English, inside the scene it
belongs to.

So: one shape per film, chosen by what the film is about, and no two films
sharing a hero image.

---

## The spine: problem, solution, underlying magic, call to action

Guy KAWASAKI's order, and every brick film follows it. A viewer who does not
know the package needs the pain before the cure, the cure before the clever
part, and something to do at the end.

**Problem.** Something concrete that goes wrong, stated as a fact about a
reader rather than a gap in a feature list. "Light grey on white reads
perfectly well. At your desk, indoors." The viewer has to recognise it.

**Solution.** What the package does about it, shown rather than listed.

**Underlying magic.** The non-obvious mechanism, the thing you would not
guess and a competitor does not have — and, since 2026-10-28, the source it
rests on, named. For `colors`: hue is what red-green blindness removes,
saturation is what grey printing removes, lightness is what nothing removes,
so all three tools work on lightness, and the matrices come out of Machado
2009, measured on real observers. `maps` names ACLED and UCDP, which both
record how well each coordinate is known while every other tool draws all of
them as the same dot. `audio` names Netflix's timed text style guide, where
seventeen characters a second and forty-two to a line come from. `figures`
ends on the Ralph Eyeball Loop, the one thing in the suite that is not a
rule. A mechanism without a source is a boast; with one it is something the
viewer can go and check.

**Call to action.** Two asks, in the order of what they cost: star the
package on GitHub, then the suite at sprezzature.ai. The star points at the
package the film is about — somebody who has just watched a minute on `maps`
wants `sprezzature-maps`, and sending them to the monorepo is a redirect
dressed up as a destination. The films used to end on "Make it. Audit it.
Then look at it.", which is a motto, and a motto asks for nothing.

### The spine is on screen

A pitch deck labels its slides. A film cannot, so these label the frame: a
rail above the picture carries PROBLEM · SOLUTION · UNDERLYING MAGIC · YOUR
TURN for the whole minute, with the current one lit in blue. At any second a
viewer wondering where this is going can see the answer without rewinding.

It is a rail and not an eyebrow on purpose. Replacing each scene's own
eyebrow with a beat label would have flattened eleven films into one
template, and the sentence in a scene's eyebrow — "Who holds what, at what
certainty" — carries more than the word "Solution" ever will.

The spine is shared. The execution is not: each film has its own scene types,
its own pictures and its own number of beats. A shared order is a way of
being understood; a shared format is a way of being skipped.

## No film opens on a blank frame

Every film used to fade its first sentence up from an empty sheet while the
wordmark waited for scene one to finish. A viewer who lands on a blank frame
has already decided what kind of video this is. The first sentence is on
screen at frame one, and the rails carry the wordmark from zero.

---

## The image allocation

No picture appears in two films. The suite film is the exception it has to be
— it is a montage of the others — so it was given the four that no brick film
uses as its own.

| Film | Pictures |
|---|---|
| sprezzature | `corr-matrix`, `calendar-heatmap`, `map-flow`, `choropleth` + the Ralph loop on `bar-grouped` |
| figures | `sankey`, `alluvial`, `chord`, `bellcurve`, `circle-packing`, `candlestick`, `clustermap`, `kde2d-contour`, `surface3d` |
| maps | the six situation plates, `choropleth-sequential`, `choropleth-diverging` |
| colors | the five colour-vision frames |
| cli-gui | the two `make-figure` captures |
| publish, audio, ux-laws, ui, accessibility, video | none — these are films about text, and a stock photograph would be a lie |

---

## The shapes

**sprezzature** — *the thesis.* Cold claim, the sources named, then sixteen
seconds of the Ralph loop, which is the one thing in the suite that is not a
rule. Ends on what nobody uploaded. Drops the "ten packages, five surfaces"
panel: a spec sheet, and the least interesting thing that was on screen.

**colors** — *mostly picture.* Opens on the failure, not on an explanation.
Twenty-two seconds of the simulator running through four kinds of eye, which
is longer than any beat in the old set. One line after it. The argument is
made by looking.

**maps** — *no panels at all.* Six plates and a voice over them. The only
text is the one sentence a plate cannot say for itself.

**ux-laws** — *one sustained argument.* No chip grid. It starts from what a
user actually says, gets to the law behind it, and stops at the boundary —
what a machine may and may not decide.

**figures** — *a catalogue, shown not counted.* Two long grids with the
pictures doing the work, and one beat on the thing that makes a hand-authored
SVG different from an exported one.

**publish** — *a pipeline.* A document moving left to right through the nine
tools and arriving as a site. New scene type: `flow`.

**audio** — *a symmetry.* Two columns, read in both directions, the same
object on each side. The film is the shape of its subject.

**cli-gui** — *before and after.* A command line on the left, the form it
became on the right. New scene type: `versus`.

**ui** — *the fewest words.* The smallest brick gets the smallest film: four
held sentences, no grid, no panel. One idea, said slowly.

**accessibility** — *source code on screen.* The markup that breaks the rule,
with the line that does it marked. New scene type: `code`.

**video** — *the film audits itself.* Claims appear and are checked against
the code as the film plays. New scene type: `verify`.

---

## Three canvases, 4K

Each film is cut wide (3840×2160), tall (2160×3840) and square (2160×2160)
off a single composition, and all three are on the site rather than only the
wide one. The three are frame-synced: the same sentence lands on the same
second whichever you watch, so the format switcher keeps the playhead where
it was.

4K goes through `--resolution <canvas>-4k`, which leaves the composition
alone and raises Chrome's device pixel ratio. It also needs
`--low-memory-mode`, and not for the reason the flag is named: the default
path writes all 1800 frames to disk before encoding, which at 3840×2160 wants
about 60 GB of scratch, and this machine has 32. Streaming encodes as it
captures. The cost is wall clock — 3m19s a cut instead of 38s, so the set
takes hours rather than minutes.

## New scene types this needs

- `flow` — labelled stages left to right, revealed in order (publish)
- `versus` — two halves with a divider and a label each (cli-gui, audio)
- `code` — a monospace block with chosen lines highlighted (accessibility)
- `verify` — claims with a value appearing beside each (video)
- `held` — one sentence, larger than `claim`, on screen long enough to read
  twice (ui)
- `cta` — the logo, the package name, and two things to do (all eleven)
