# Plain-language rewriter: `plain_language.py`

Rewrite any UI copy at a target reading level using the same local Ollama model the skill uses for alt text. Keeps the meaning verbatim; strips jargon and marketing voice.

## Why it matters

Cognitive accessibility is the WCAG criterion almost nobody ships. The relevant Success Criteria are:

- WCAG SC 2.4.5 (Multiple ways).
- WCAG Understanding 3.1.5: Reading Level.

Users who benefit beyond cognitive disabilities: second-language readers, anyone reading under stress (medical sites, financial sites, government UIs), and screen-reader users whose focus is already split. The rewrite is cheap to add because the model runs locally and the same setup as `alt_from_ollama.py` is reused.

## Install

If you've already run `python sprezzature-vision/scripts/install_alt_ai.py` for alt text, you're done; the same Ollama daemon and model serve the rewriter. If not:

```bash
pip install -r scripts/requirements-plain-language.txt
python sprezzature-vision/scripts/install_alt_ai.py
```

## Run

```bash
# Pipe a single string
echo "Boost your productivity with our state-of-the-art platform" \
  | python scripts/plain_language.py --target-grade 8 --lang en

# Read a file
python scripts/plain_language.py --input src/copy.md > dist/copy.simple.md

# Keep brand names intact
python scripts/plain_language.py --preserve "Sprezzature,Tailwind,Montserrat" --input copy.md

# Bypass cache for this run
python scripts/plain_language.py --no-cache --input copy.md
```

The output prints to stdout. The script does NOT overwrite your file.

## Default rules the rewriter enforces

1. Preserve meaning EXACTLY: no added facts, no removed facts, no changed numbers / names.
2. Use short sentences, common words, active voice.
3. Strip marketing buzzwords. The script bans the same list of words the validator flags (`production-grade`, `non-negotiable`, `world-class`, `cutting-edge`, `seamlessly`, `leverages`, `boost`, `unleash`, `transform`, `revolutionize`, …).
4. Don't add headers or bullets that weren't in the source.
5. Keep tokens listed in `--preserve` verbatim: brand names, code identifiers, API names.
6. Output length stays within `1.1 × source length`; if the model overshoots, the script asks again once with a tighter constraint.

## When to use vs. when not to

| Use it for | Don't use it for |
|---|---|
| Marketing landing copy | Legal contracts (rewording can shift legal meaning) |
| Error messages | Medical or safety-critical instructions (review by a domain expert) |
| Empty states | Brand voice work that depends on a specific register |
| Form labels and help text | Code comments (rewriter targets prose, not code) |
| Documentation prose | Strings under translation review (rewriter loses translator context) |
| README intros | Citations or quoted material (rewriter would paraphrase) |

## Multilingual

The script honors `--lang` (or falls back to the detected system locale). The prompt is anchored in the target language so French in returns French out. The 10 languages with explicit prompt instructions are: en, fr, es, de, it, pt, nl, ar, ja, zh. Additional languages fall back to the English instruction (the model still tends to reply in the source language).

## Cache

Same shape as the alt-text helper:

- Location: `~/.cache/sprezzature-skill/plain/` (override with `SPREZZATURE_CACHE_DIR`).
- Key: SHA-256 of `text + target_grade + lang + sorted(preserve) + model`, truncated to 32 hex.
- Bypass: `--no-cache` or `SPREZZATURE_NO_CACHE=1`.
- Clear: delete the directory.

## Programmatic use

```python
from plain_language import rewrite

simple = rewrite(
    "Leverage our cutting-edge platform to boost your productivity",
    target_grade=8,
    lang="en",
    preserve=["Sprezzature"],
)
```

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Output longer than input × 1.5 | First retry didn't help; model is over-explaining | Lower the source's complexity or call with a tighter `--target-grade`. |
| Output stays nearly identical | Source is already plain | Expected; no action needed. |
| Names get translated | `--preserve` not set | Add the names to `--preserve`. |
| Wrong language out | `--lang` mismatched the source | Set `--lang` explicitly. |
| `Cannot reach Ollama at http://localhost:11434` | Daemon not running | `ollama serve` or re-run the installer. |

## Checklist

- [ ] `--lang` matches the source language.
- [ ] Brand names and identifiers in `--preserve`.
- [ ] Output length close to source (≤ 1.1×).
- [ ] No buzzwords in the output (`python sprezzature-ui/scripts/validate.py` will catch them if the file is committed).
- [ ] Numbers and names preserved verbatim.
- [ ] Cache hit on second run (≤ 100 ms).
