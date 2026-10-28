# Eleven pitches

Written 2026-10-28, with each brick's repository open beside it. Every line
below was taken from the package it describes — its README, its module
docstrings, the comment above the rule — rather than from a feature list.
That is the whole method, and it is why most of these sentences were already
written: the best one in a package is usually sitting in a docstring nobody
watching a film will ever open.

Guy KAWASAKI's order throughout: **problem**, **solution**, **underlying
magic**, **call to action**. The viewer needs the pain before the cure, the
cure before the clever part, and something to do at the end.

## What makes each beat good enough to keep

**A problem** is something that goes wrong for a reader, stated as a fact
about them rather than a gap in a feature list. "Light grey on white reads
perfectly well. At your desk, indoors." You have to recognise it before you
are told what it costs.

**A solution** is what the package does about that, shown rather than
listed. No bullet points of capability.

**Underlying magic** is the mechanism you would not guess, *and the source it
rests on, named*. A mechanism without a source is a boast. With one it is
something a viewer can go and check, which is a different kind of claim.

**The call to action** is two asks, in the order of what they cost: star the
package on GitHub, then the suite at sprezzature.ai. The star points at the
package the film is about, because somebody who has just watched a minute on
`maps` wants `sprezzature-maps`.

---

## sprezzature — the suite

| | |
|---|---|
| **Problem** | Nearly every design decision has already been made, and settled in public: the laws of attention by Yablonski, contrast by the W3C, what a colour-blind reader sees by a 2009 paper. Published years ago. Your tools have never heard of any of it. |
| **Solution** | It is code now, pointed both ways — at the thing you are making, and at the thing that is already live. 167 chart kinds, 20 accessibility rules, 30 laws of UX. |
| **Underlying magic** | The Ralph Eyeball Loop: the one thing in the suite that is not a rule. A vision model looks at the finished picture, says what is wrong with it, and what you then fix is the source. Everything stays on your machine. |
| **Source** | Jon Yablonski, *Laws of UX*; WCAG; Machado, Oliveira & Fernandes 2009; Equal Earth (Šavrič, Patterson & Jenny, 2018). |

## colors — `sprezzature-colors`

| | |
|---|---|
| **Problem** | Light grey on white reads perfectly well, at your desk, indoors. Whoever chose the colour can read it: that is the whole problem. Outside in full sun the screen flattens the difference, and about one man in twelve does not separate red from green at all. |
| **Solution** | Three deterministic tools on the standard library: a contrast audit that proposes a fix staying visually close to your colour, a simulator that redraws the picture the way that eye actually sees it, and a Tailwind export so every project draws from one palette. |
| **Underlying magic** | Hue is what red-green blindness removes. Saturation is what grey printing removes. Lightness is what nothing removes — so all three tools work on lightness, and your blue stays your blue while it becomes legible. That sentence sat in a module docstring until the first rewrite found it. |
| **Source** | Machado, Oliveira & Fernandes 2009, matrices measured on real observers; WCAG contrast thresholds. |

## ux-laws — `sprezzature-ux-laws`

| | |
|---|---|
| **Problem** | They will tell you the page is overwhelming. They will tell you they can never find the button. Nobody will ever say "Hick's Law". |
| **Solution** | Thirty laws collected by Jon Yablonski; eight of them decidable from the HTML text alone, with no browser and no rendering, fast enough for a pre-commit hook. |
| **Underlying magic** | Hick's Law measures the choices a person faces **at one moment**, so counting the links in a file gets it wrong twice. A responsive header holds two menus that never appear together, so the auditor resolves each control's visibility and reports the worse of the phone count and the desktop count, naming which. And a `<details>`, a `<menu>` or a `role="radiogroup"` is one choice however much it contains. |
| **Source** | `references/laws-of-ux.md`, each law with its paper. |

## figures — `sprezzature-figures`

| | |
|---|---|
| **Problem** | You have a spreadsheet and no idea which chart is the right one, so you reach for the bar chart you reached for last time. |
| **Solution** | 167 kinds, every one hand-authored SVG with no charting library underneath, so the text in the figure stays text — selectable, searchable, readable by a screen reader. |
| **Underlying magic** | Each kind declares the data roles it needs, so your columns decide rather than a template: three of them fill sixty-one kinds, ranked by readability, deterministically and with no model involved. Then the Ralph Eyeball Loop asks a model the one question the ranking cannot answer — is this actually readable — and never lets it contradict a fact the linter established. |
| **Source** | `FIGURES.md`, 167 kinds across 52 categories, each with when to use it. |

## publish — `sprezzature-publish`

| | |
|---|---|
| **Problem** | A page that reads itself aloud and highlights the sentence as it goes. One sentence out of step is worse than no highlighting at all: it points at the wrong line, with confidence. |
| **Solution** | Nine tools turn a README and a `docs/` folder into a site: pages, meta tags, a favicon set from one logo, the indexes a crawler wants and the two files a language model reads, a feed, and the narration with its read-along. |
| **Underlying magic** | The audio and the page leave the same Markdown by different roads — sentences to the voice engine, blocks walked as a tree — so the module refuses to number the sentences on its own side. It compares the two lists and raises on the first divergence. There is no third outcome. |
| **Source** | Open Graph, Twitter Card, Schema.org, `llms.txt`, Atom. |

## audio — `sprezzature-audio`

| | |
|---|---|
| **Problem** | Your video has captions and they are accurate. Ninety characters, on screen for half a second. Nobody reads that. Accuracy was the only thing anybody measured. |
| **Solution** | Seven scripts, all local: what was said, who said it, in which language — and the same modality read backwards, text into speech, landing as a WAV plus a WebVTT exactly as a transcript does. |
| **Underlying magic** | The numbers already exist and have a publisher. Seventeen characters a second, forty-two to a line, five sixths of a second at the shortest, seven at the longest, two lines at most. Conventions rather than laws, which is why each one is a flag: a children's programme and a dense talk justify different numbers. |
| **Source** | Netflix Timed Text Style Guide; BBC agrees on the two-line rule. |

## cli-gui — `sprezzature-cli-gui`

| | |
|---|---|
| **Problem** | Your colleague needs this tool and will not open a terminal. |
| **Solution** | The command generates its own page: options become fields, choices become a list, required stays required. The page never runs anything — it assembles the exact command line in the visitor's browser, ready to copy, to hand to a desktop wrapper, or to post to an endpoint that runs it for real. |
| **Underlying magic** | Three frameworks, two adapters, because a Typer app is already Click once you ask it. And one detail decides whether the page tells the truth: a Click group takes its name from the decorated function, which is almost never the command you installed — unasked, the page would build a command line that does not exist. |
| **Source** | `argparse`, `click` and `typer` walked directly; `--from-help` for `cobra` and `clap`, lower fidelity and honest about it. |

## ui — `sprezzature-ui`

| | |
|---|---|
| **Problem** | A sentence written straight into a template costs nothing today. It costs a week the day somebody needs a second language and the strings turn out to be scattered through JavaScript literals, HTML attributes and prompt templates buried in Python. |
| **Solution** | One catalogue, and an audit cheap enough for a pre-commit hook that finds every string belonging in it — including the model prompts, which are translatable strings almost nobody treats as one. |
| **Underlying magic** | `--fix` writes the string into the catalogue and then stops. It will not rewrite your call site, for the reason `pybabel extract` gives: only the author knows which id the call should use, and whether the surrounding code wants a plural or a placeholder. So it prints the line to paste, and anything it could not parse with certainty is reported as needing a hand rather than dropped in silence. |
| **Source** | `audit_i18n.py`, and the GNU gettext convention it follows. |

## maps — `sprezzature-maps`

| | |
|---|---|
| **Problem** | A column of countries hides where things actually happen. |
| **Solution** | Three generators drawing real coastlines on a real projection, every line written by our own code with no charting library underneath: a choropleth that names its classification method, a situation plate that centres itself on its region, and an accumulation field. |
| **Underlying magic** | ACLED and UCDP both record, beside every coordinate, **how well that coordinate is known** — ACLED's `geo_precision` 1–3, UCDP's `where_prec` 1–7, where a 3 is a provincial capital standing in for a whole province. Tools that plot this data draw all of them as the same dot, asserting a street corner the source never gave, once per row. Here a named place is a solid cased disc, an approximate one a hollow ring, a region pinned to its capital a broken ring, and a stated radius is drawn. The density plate goes further and draws no map at all: no coastline, no border, no graticule. The land appears because events fell on it. |
| **Source** | ACLED codebook; UCDP GED; Natural Earth; GMTED2010; HydroRIVERS and HydroSHEDS; Equal Earth and Lambert conformal conic. |

## accessibility — `sprezzature-accessibility`

| | |
|---|---|
| **Problem** | A video starts playing by itself, with sound. A blind reader now cannot hear the screen reader they would use to find the stop button. The trap closes on itself. |
| **Solution** | Twenty rules, each decidable by reading the HTML text: no browser opens, no page renders, no JavaScript runs, nothing to install beyond Python. Each finding names the element, the line, and the rule. |
| **Underlying magic** | Six of the twenty repair themselves, and only six, because a repair is automatic solely where exactly one repair is safe; the other fourteen are reported and never guessed at. `--fix-alt` is the exception that proves the rule — it drafts the missing alt with a local vision model using the image **and** the surrounding text of that same page, because neither alone is enough. |
| **Source** | WCAG and WAI-ARIA, rule by rule. |

## video — `sprezzature-video`

| | |
|---|---|
| **Problem** | A film asserts things at thirty frames a second and burns them into pixels, where nothing ever reads them again. Prose in a README gets re-read; a number in a keyframe does not. This suite told viewers it had 127 chart kinds for months after it had 167, baked into ten compositions and five MP4s, and nothing anywhere was watching. |
| **Solution** | Not a renderer. A checker that holds a film's assertions against the code they describe, in both directions, with the renderer behind a seam because which tool grabs the frames is the least interesting decision here. |
| **Underlying magic** | The dangerous claim is the undeclared one. A declared claim gets checked against the file that would have to change for it to stop being true. A number that merely appears on screen has nothing behind it at all, so the scan reads the composition and reports every number no claim accounts for. And the poster is baked as frame zero, because Slack, X and Discord regenerate their thumbnail server-side from the first frame whatever a `poster=` attribute says. |
| **Source** | The repository's own history, which is where the 127 came from. |

---

## What that last row cost to find

`sprezzature-video` is the brick that says the first frame of a film is the
frame most likely to be seen on its own. Every one of these eleven films
opened on a half-faded sentence over a sheet with no wordmark on it, and had
done since the set was cut. Reading the package in order to pitch it is what
found that, which is an argument for the method on its own.
