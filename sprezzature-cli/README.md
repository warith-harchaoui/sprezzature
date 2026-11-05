# sprezzature-cli

A thin top-level driver for the ten [`sprezzature`](https://github.com/warith-harchaoui/sprezzature) bricks.

```bash
pip install ./sprezzature-cli         # from the repo root
```

Then:

```bash
sprezzature --help                    # every sub-command, across the ten bricks
sprezzature --version

sprezzature ui i18n-audit src/        # → sprezzature-ui-i18n-audit src/
sprezzature ui i18n-make              # → sprezzature-ui-i18n-make

sprezzature accessibility lint public/  # → sprezzature-accessibility-lint public/
sprezzature vision alt photo.jpg --kind informative --lang en   # → make-alt
sprezzature colors contrast --palette palette.json
sprezzature colors cvd screenshot.png
sprezzature audio captions video.mp4 --format vtt

sprezzature publish favicons logo.png --out public --name "Project"
sprezzature publish meta page.html
sprezzature publish indexes --root . --base-url https://example.com
sprezzature publish plain --input copy.md
sprezzature publish lint-md docs/
sprezzature publish md-to-html README.md

sprezzature figures …                 # → sprezzature-figures …
sprezzature maps …                    # → sprezzature-maps …
sprezzature video …                   # → sprezzature-video …
sprezzature cli-gui …                 # → sprezzature-cli-gui …
sprezzature ux-laws …                 # → sprezzature-ux-laws …
```

The driver **shells out** to each brick's own command; it does not duplicate
any logic. The last five forward every argument to the brick's front door,
whose `--help` lists its tools.

## How it finds a tool

Each sub-command tries, in order:

1. the brick's console script on `$PATH` (`sprezzature-accessibility-lint`, …);
2. `<skill>/scripts/<script>` inside a skill folder found on
   `$SPREZZATURE_SKILLS_PATH` (colon-separated parent directories), the
   current directory, `~/.claude/skills/` or `~/.opencode/skills/`: the
   pre-split layout, kept for hand-built folders;
3. `python -m <module>` against the brick's installed package.

When none resolves, it exits 2 and names the `pip install` that fixes it.

## Why this exists

Before `sprezzature-cli`, users ran each script directly:

```bash
sprezzature-accessibility-lint public/
sprezzature-publish-icons logo.png --out public
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

The same `_<TOOL>_COMPLETE=<shell>_source` trick works for every brick's own
command, since they are all Click:

```bash
_SPREZZATURE_ACCESSIBILITY_ALT_COMPLETE=zsh_source sprezzature-accessibility-alt > ~/.alt-complete.zsh
_SPREZZATURE_AUDIO_CAPTIONS_COMPLETE=zsh_source sprezzature-audio-captions > ~/.captions-complete.zsh
```

These commands print the completion snippet to stdout; nothing is installed,
modified, or downloaded.

## License

BSD-3-Clause (same as scikit-learn, and the rest of the `sprezzature` repo).
