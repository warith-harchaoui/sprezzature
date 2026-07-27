# BSD 3-Clause License

Copyright (c) 2026, Warith Harchaoui

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

This is the same license used by **scikit-learn**.

---

## Bundled third-party assets

The BSD-3-Clause above applies to the source of this repository.
Bundled third-party assets retain their own licenses:

- **Roboto / Roboto Serif / Roboto Mono** (typefaces) — bundled in
  `sprezzature-ui/assets/fonts/roboto/`, `sprezzature-ui/assets/fonts/roboto-serif/`,
  and `sprezzature-ui/assets/fonts/roboto-mono/` under the **SIL Open Font
  License (OFL)** (the "three-Roboto rule"). The full license and its
  required copyright notice are in the `OFL.txt` shipped in each of the
  three folders.

- **Common Voice audio clips** — extracted into
  `tests/fixtures/audio/cv/<lang>/` from Common Voice 26.0, obtained
  via [Mozilla Data Collective][mdc] under the dataset's **CC0 1.0
  Universal** dedication (public domain). The clips themselves are
  redistributable for any purpose, commercial or non-commercial, with
  no attribution requirement. Attribution to Mozilla and the Common
  Voice contributors is provided here as good practice, not as a
  license obligation. Per the Mozilla Data Collective platform terms
  and the spirit of contributor consent, **we do not attempt to
  identify or re-identify speakers**; the per-language `MANIFEST.json`
  records the Common Voice opaque `client_id` hash for reproducibility
  only, never raw identifiers. Contributors withdrawing consent
  upstream should refresh fixtures by re-running
  `tests/fixtures/audio/extract_cv_subset.py` against the latest
  release.

[mdc]: https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk
