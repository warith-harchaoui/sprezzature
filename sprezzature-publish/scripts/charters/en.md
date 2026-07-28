<!--
Writing charter — English (lang code: en).

This is the load-bearing source the writing-standards layer reads at run time:
meta_from_ollama, plain_language, lint_markdown captions, and the prose Ralph
loop all enforce it. Authored natively in English, not translated. Keep it in
sync with the project charter of record (gist f45304d066abc81dd7d4f059a1f4e45f).
See ../../references/writing-standards.md for how it is applied.
-->

# Writing charter — English

A writing charter for **any text** in English: article, chapter, note, email, post,
or the write-up of a conversation with a language model. It is self-contained: the
clarity method and the coherence rules are integrated here, with no other file to
open. Written natively in English, not translated. Apply it concept by concept,
line by line.

## 1. The principle: make it reconstructible

To understand is not to remember a formula; it is to be able to rebuild it and
explain it to someone who knows nothing. A good text does more than inform: it
leaves the reader able to redo the reasoning alone.

The novice test: if you cannot explain it simply, you have not understood it. The
place where you hide behind a learned word is a gap in understanding, not an
elegance; jargon is not a shortcut, it is a hiding place. When a sentence does not
flow without an unexplained term, go back to the source until it does.

## 2. What is worth writing: originality and importance

Before knowing how to say it well, know whether the point is worth making. Two
questions, held together:

- **Originality.** Does the point already exist as such in the common literature, or
  is it framed in a way with no accessible equivalent? A point wholly available
  elsewhere adds little; a framing, a series drawn together, a reformulation that
  illuminates, add much. A good reformulation is itself original work: the merit often
  lies in the angle, not the bare fact.
- **Importance.** Is the stake marginal (a setting, a detail) or structural (a
  responsibility, a sovereignty, a collective health, an economy)? Spend the writing
  effort where the stake warrants it.

Honesty guard: never present as new what already exists. Before claiming novelty, check
it has not been stated elsewhere; when in doubt, stand as the interpreter who gives the
clear reading, not the inventor. Oversell nothing.

## 3. The per-concept loop

For each notion (technical word, acronym, formula, standard, proper name):
1. **Name** the concept.
2. **Explain it in plain language**, as to a beginner, with no undefined term.
3. **Find the friction point**: the word or leap where the explanation stalls. That
   is where the obscurity hides.
4. **Fill, then simplify**: go back to the source, then restate with an intuition in
   words and a concrete example, until the account is continuous.

An example of the gesture. *Before*, starting from the formula: "We optimize a proxy
under a perimeter constraint." *After*, starting from the intuition: "We track a
stand-in measure, something easy to quantify that we watch in place of the real goal we
cannot measure directly; rewarding every bug fixed, for instance, ends up encouraging
new bugs to fix." The second version names the concept, puts it in words, gives a
concrete case, flags the trap in passing, with no term left bare.

## 4. Per-concept checklist

- **Intuition first.** An image or idea in words precedes any formula or abstraction.
  The formula comes last, the compact summary of something already understood, never
  the starting point.
- **One concrete example.** Every idea gets at least one example a non-specialist can
  picture (an everyday object, a worked figure, a scene).
- **No bare jargon.** Every technical term is glossed at first appearance; the reader
  never needs a glossary to follow.
- **Acronyms.** A plain-language gloss first, then the real term, then only the
  abbreviation: "reinforcement learning with humans in the loop (RLHF)." Keep the true
  term of art; never swap it for a forced paraphrase that loses its technical precision.
- **First principles.** The concept is derived from a simple base already laid, not
  from an authority or another obscure term.
- **Anchor the new on the known.** Every new notion attaches to something the reader
  already holds, rather than floating alone.

## 5. Analogies (the A/B/C/D method)

An analogy of relation carries a property from a known pair to one to be lit: as A is
to B, so C is to D. It puts four terms in play; it is the relation between A and B that
transfers to C and D. Before using one, you should be able to answer three questions:
what are the four terms? what property carries from A–B to C–D? where does the likeness
stop holding?

Two opposing demands, held together:
1. **Name the four terms and the carried property early, in prose**, so the reader
   sees what is set against what. If they do not, the analogy floats and the reader
   drops it.
2. **Never lay them out as labels.** Writing "A is to B as C is to D," aligning
   letters or a ratio, makes the device visible and mechanical; the reader rejects it.
   Clarity comes from the prose, not the scaffolding.

Rule: **clear, never explicit.** The reader should be able to rebuild the likeness
alone, without being shown the A/B/C/D frame. And since every analogy eventually gives
way, say exactly where it stops holding.

Example. "Just as a hospital, fed by a reliable power grid, still keeps a backup
generator so as not to depend on a single source, an organization that entrusts a vital
function to a remote service needs a local fallback." The four terms (grid and hospital
on one side, remote service and organization on the other) and the carried property
(the need for a backup when the infrastructure is vital) are plain, without a single
letter or ratio. And you say where it breaks: the generator restarts identically, a
software fallback is often degraded.

## 6. Coherence and honesty

- **Invent nothing.** Clarify and develop what is there; add no unverifiable fact.
  Where understanding stops, say so.
- **Mark the evidence status.** Always distinguish the *observed*, the *measured*, the
  *extrapolated* and the *speculative*; an empirical claim never appears without its
  degree of certainty.
- **Do not impute intention without flagging it.** Never attribute will or agency to a
  system as if it were a fact; if you use such a shortcut, mark it as one.
- **The counterexample that teaches.** A rule is often grasped best at the point where
  it breaks: a real case that went wrong, quantified and sourced, teaches better than
  the success. Two conditions so that it carries rather than decorates: it illustrates a
  thesis already stated, it does not replace it; it is solidified like any reference
  (exact figures, primary source, a link that resolves). A loose counterexample turns
  against the argument.
- **A measured stance.** No excess either way; do not slide into the camp that
  simplifies. Thinkers are used as readings, not as endorsements.
- **One concept, one place.** A notion is defined once; elsewhere you point back to it
  rather than redevelop it. Nothing silently contradicts what was held earlier.

## 7. Form

- **No punctuation dashes.** No em dash, no en dash used as an aside. Rewrite with
  commas, colons, semicolons, parentheses, short sentences. Hyphens in compounds
  (socio-technical, decision-making) stay.
- **English punctuation, not French.** The rules differ from French and none of the
  French habits carry over. No `«  »` guillemets: use straight double quotes (or the
  file's `\enquote{...}`). No space before `; : ? !` and no space inside quotation
  marks (French insécables do not apply). Commas and periods sit tight against the
  word. Do not transplant a French sentence's punctuation into the English one.
- **No machine tics:** no ", and" or ", or" welding two clauses (split the sentence,
  or use a semicolon or colon), no "In other words," no "In a word," no reflexive
  rule of three, no italics-for-emphasis by habit, no inflated turns of phrase.
- **No antithesis reflex.** The turn "it is not X, it is Y," "not X but Y" laid down by
  habit is a template's signature. Keep it only where the opposition is real and carries
  the argument, never as a see-saw effect.
- **No marathon sentences.** A sentence running past roughly ten lines on screen forces
  disproportionate effort, however grammatical. Cut it in two or restructure. Beware too
  of disguised lists, sentences that thread an enumeration through continuous syntax:
  make a real list or separate sentences. Length is not depth.
- **No lexical tic.** A verb or turn that keeps returning ("shift," "at once,"
  "precisely," "enables") betrays the template. Hunt echoes by search and vary them,
  unless the repetition is a deliberate motif.
- **A sober, human, elevated register.** Never "LLM-ish," "ChatGPT-ish" or
  "Claude-ish." The sentence must sound like an author's, not a template's.
- **Hunt the ChatGPT tells.** They give the machine away and vanish on rereading:
  - hollow openers: "In today's world," "In an era where," "It's important to note
    that," "It's worth noting that," "Needless to say";
  - bolted-on transitions when no real link calls for them: "Moreover," "Furthermore,"
    "Additionally," "In essence," "Ultimately," "At the end of the day";
  - restatement tics: "In other words," "Simply put," "To put it another way";
  - empty intensifiers laid on for weight: "truly," "deeply," "profoundly,"
    "fundamentally," "literally," "crucial," "pivotal," "vital";
  - reflexive see-saw: "not only X but also Y," "it's not just about X, it's about Y";
  - hollow closers: "In conclusion," "Ultimately," "All in all";
  - inflated abstractions: "the landscape of," "at the heart of," "the realm of," "the
    fabric of," "navigate the complexities of," "delve into," "a game-changer";
  - regular symmetry and rule-of-three rhythm that smooth the prose into anonymity.

  The fix is not another ready-made phrase; it is a situated sentence, irregular in
  rhythm, that says the thing and no more. An author's prose has edges.

## 8. Idiom

As idiomatic as possible. Always prefer the phrasing an educated native speaker would
use over the correct but flat one. Straight, natural English; no French quotation
marks or spacing carried over.

## 9. Sources

No gratuitous reference. A citation says what the source establishes, by what method,
with what limit, and why it is decisive at that spot. You actually read the source
before using it. Ban "as X so aptly puts it" and decorative name-dropping. One strong
citation per claim.

At equal relevance, balance the voices: when several sources carry equal authority,
gladly cite the women authors of reference where they exist. Never drop a source for
this reason; it is an attention to balance, not a quota.

## 10. The Ralph loop: flow by paragraph pairs

Reread a text not paragraph by paragraph but by pairs of consecutive paragraphs, since
flow lives at the seam, not inside a block. The loop, borrowed from "render, look, fix
the code, repeat":

1. **Read aloud** paragraph *n* followed by paragraph *n+1*, in one breath.
2. **Look at the seam:** does the move from one to the other carry itself? Does the
   first call for the second? Is there a repeat, a logic gap, a jump, a word echoed
   across the two blocks, a bolted-on transition ("moreover," "furthermore") papering
   over a missing link?
3. **Fix the prose, never the impression:** touch the text itself (order of sentences,
   the last line of *n*, the first of *n+1*, a callback, a cut); do not merely note
   that "it snags."
4. **Reread the pair,** then **shift by one:** slide to the pair (*n+1*, *n+2*) and
   start again. The windows overlap, so every paragraph is tested twice, once as an
   arrival, once as a departure.

Stay on a pair until the seam vanishes, then move on. The text flows when no join shows.

## 11. The gesture, in one image

The cook who **publishes the recipe** rather than the chef who guards the secret: show
every step, from first principle to result, so the reader can make the dish alone. A
passage is ready when a non-specialist, having read it once, could explain it in turn.
