# sprezzature-cli

A thin top-level driver for six of the [`sprezzature`](https://github.com/warith-harchaoui/sprezzature) skills.

```bash
pip install ./sprezzature-cli         # from the repo root, or
pip install sprezzature-cli           # from PyPI when published
```

Then:

```bash
sprezzature --help                    # discoverable sub-commands across all six wired skills
sprezzature --version

sprezzature ui validate               # → python sprezzature-ui/scripts/validate.py

sprezzature accessibility lint public/  # → python sprezzature-accessibility/scripts/lint_a11y.py public/
sprezzature colors contrast --palette palette.json
sprezzature colors cvd screenshot.png
sprezzature vision alt photo.jpg --kind informative --lang en
sprezzature audio captions video.mp4 --format vtt

sprezzature publish favicons logo.png --out public --name "Project"
sprezzature publish meta page.html
sprezzature publish indexes --root . --base-url https://example.com
sprezzature publish plain --input copy.md
```

The driver **shells out** to each existing script — it does not duplicate any
logic. The validators (`validate`, `lint`, `contrast`, `cvd`, `indexes`) stay
stdlib-only when invoked directly, even if `sprezzature-cli` itself depends on Click.

## How it finds the skills

`sprezzature-cli` looks for each skill folder in this order:

1. `$SPREZZATURE_SKILLS_PATH` (colon-separated list of parent directories).
2. The current working directory (useful when running inside the repo).
3. `~/.claude/skills/`.
4. `~/.opencode/skills/`.

If a skill is missing, the relevant sub-command says so and points at the
install instructions.

## Why this exists

Before `sprezzature-cli`, users ran each script directly:

```bash
python sprezzature-accessibility/scripts/lint_a11y.py public/
python sprezzature-publish/scripts/favicons.py logo.png --out public
```

That works, but it leaks the skill layout and there's no single `--help`
to discover available actions. `sprezzature-cli` collapses the surface to a
single `git`-style command, ships `--version`, and (when installed via
`pip install`) wires shell completion automatically through Click.

## Shell completion

Click ships completion scripts for `bash`, `zsh`, and `fish`. Generate
one once, source it from your shell rc, and tab-completion for `sprezzature`
sub-commands + options Just Works.

```bash
# Bash
_SPREZZATURE_COMPLETE=bash_source sprezzature > ~/.sprezzature-complete.bash
echo 'source ~/.sprezzature-complete.bash' >> ~/.bashrc

# Zsh
_SPREZZATURE_COMPLETE=zsh_source sprezzature > ~/.sprezzature-complete.zsh
echo 'source ~/.sprezzature-complete.zsh' >> ~/.zshrc

# Fish
_SPREZZATURE_COMPLETE=fish_source sprezzature > ~/.config/fish/completions/sprezzature.fish
```

The same `_<TOOL>_COMPLETE=<shell>_source` trick works for the per-script
CLIs that were migrated to Click — useful if you invoke them directly
rather than through the `sprezzature` driver:

```bash
_ALT_FROM_OLLAMA_COMPLETE=zsh_source alt_from_ollama.py > ~/.alt-complete.zsh
_CAPTIONS_FROM_WHISPER_COMPLETE=zsh_source captions_from_whisper.py > ~/.captions-complete.zsh
_META_FROM_OLLAMA_COMPLETE=zsh_source meta_from_ollama.py > ~/.meta-complete.zsh
_PLAIN_LANGUAGE_COMPLETE=zsh_source plain_language.py > ~/.plain-complete.zsh
```

These commands invoke the script with a special env var so Click prints
the completion shell snippet to stdout — nothing is installed, modified,
or downloaded.

## License

BSD-3-Clause (same as scikit-learn, and the rest of the `sprezzature` repo).
