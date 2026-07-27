# Large language model (LLM) choice — Qwen3-VL 8B (Q4_K_M) via Ollama

> **The whole `front-*` repo uses exactly one model: `qwen3-vl:8b`** (Qwen3-VL
> 8B, Q4_K_M quantization) served locally through Ollama. One model for text
> *and* vision. No second model, no cloud application programming interface (API), no MLX. This document records
> **why**, with sources.

The rule is machine-enforced by [`tests/test_single_llm.py`](../tests/test_single_llm.py):
every Ollama-backed script must declare `qwen3-vl:8b` and nothing else.

---

## What it does in this repo

`qwen3-vl:8b` is a **vision-language model (VLM)**: it accepts both text and
images, so a single model covers every task that used to need two:

| Task | Skill | Uses |
|---|---|---|
| Draft W3C alt text from an image | `sprezzature-vision` | vision + text |
| Translate captions to a second track | `sprezzature-audio` | text |
| Infer a speaker name from a transcript | `sprezzature-audio` | text |
| Draft page metadata / narration hints | `sprezzature-publish` | text |
| Plain-language rewrite | `sprezzature-publish` | text |
| Ralph Eyeball Loop `--local` visual critique | `sprezzature-figures` | vision + text |

One model, one daemon, one tag, for the agent loop and every skill script.

---

## The four selection criteria

The choice was made against four criteria, in the order that matters for a
bilingual (French / English), image-heavy, local toolkit that runs on a
Mac:

1. **Vision:** genuine understanding of layout, hierarchy, and UI elements
   (needed for the Ralph Eyeball Loop: "is the call-to-action above the fold?").
2. **French:** idiomatic French generation (alt text, caption translation)
   is non-negotiable for a bilingual project.
3. **OCR / charts:** reading dense text: axis labels, tick values, chart
   captions, screenshot text. This is the core of visual critique.
4. **Mac fit:** runs comfortably on Apple Silicon unified memory via Ollama,
   no special toolchain.

---

## Scored comparison (≈8B tier, local, 2026)

| Model | Vision | French | OCR/charts | Mac fit | Verdict |
|---|---|---|---|---|---|
| **Qwen3-VL 8B** (chosen) | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | **Winner** |
| Qwen2.5-VL 7B | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️½ | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | Prior generation, superseded |
| Gemma 3 12B | ⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️ | Best French, weak on charts |
| InternVL3 8B | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️ | Strong vision, mediocre French |
| MiniCPM-V 4.5 8B | ⭐️⭐️⭐️⭐️ | ⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️ | Document king, weak French |
| Pixtral 12B (Mistral) | ⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️ | ⭐️⭐️⭐️½ | French lab, but OCRBench ~685 |

### Concrete benchmark numbers (Qwen3-VL 8B, Instruct)

- **DocVQA:** 96.1%
- **OCRBench:** ~89.6% (≈896)
- **ScreenSpot** (UI element grounding): 94.4%
- **Multilingual:** OCR across 32 languages; French substantially improved over
  the 2.5 series (French MMBench 72.47 even at the 2B size).
- **Context window:** 256K tokens (expandable).

### Why it wins on *these* criteria

Qwen3-VL 8B is the only ≈8B model that is **top-tier on vision + OCR/charts +
Mac-fit simultaneously**, while being **strong (not merely adequate) on
French**. The v3 generation specifically fixed the multilingual weakness that
made the 2.5 series only "good" at French, without giving up the OCR/chart
crown that the Ralph Eyeball Loop depends on.

---

## Why not the alternatives

| Alternative | Beats Qwen3-VL on… | …but loses on |
|---|---|---|
| **Gemma 3 12B** | idiomatic French prose | OCR/charts (the core need), heavier |
| **Pixtral 12B** (Mistral, French lab) | French license / provenance | OCRBench ~685 vs ~896; larger |
| **Mistral Large 3** | French, vision | 675B MoE; **cannot run on a Mac** |
| **Mistral OCR 4** | raw OCR extraction | **cloud API, not local/offline** |
| **MiniCPM-V / InternVL3** | raw vision benchmarks | French is a weak spot |
| **PaddleOCR-VL / HunyuanOCR** (specialist OCR) | pure text extraction | no layout reasoning, no French generation; can't be a *single* model |
| **Phi-4 Multimodal / DeepSeek-VL2** | size / speed | French and OCR/charts both weaker |

The recurring theme: models that beat Qwen3-VL on one axis lose badly on
another. For a **single** model serving a bilingual, image-heavy, Mac-local
toolkit, the best *simultaneous* score across all four axes wins; and that is
Qwen3-VL 8B.

---

## Quantization: Q4_K_M

The Ollama tag `qwen3-vl:8b` ships **Q4_K_M by default**, the right choice:

| Quant | Disk | Quality vs FP16 | Notes |
|---|---|---|---|
| **Q4_K_M** (default) | **~6.1 GB** | ~96% | The sweet spot; comfortable on 16 GB unified memory |
| Q8_0 | ~8.2 GB | ~99% | Only worth it on 32 GB+; ~3–4% quality gain for nearly double the RAM |
| FP16 | ~16 GB | 100% | Overkill for local use |

`ollama pull qwen3-vl:8b` gets you Q4_K_M; nothing else to specify.

---

## Setup

```bash
# Install Ollama (once) — https://ollama.com/
ollama serve                 # start the daemon (keep running)
ollama pull qwen3-vl:8b      # ~6.1 GB, Q4_K_M
```

Every skill talks to `http://localhost:11434` by default (override with
`OLLAMA_URL`). The model tag is fixed; there is intentionally **no `--model`
CLI flag**, and `OLLAMA_MODEL` survives only as a bare test seam.

---

## Sources

Research behind this decision (2026):

- [Qwen3-VL 4B vs 8B — benchmarks, VRAM, which to run (CodersEra)](https://codersera.com/blog/qwen3-vl-4b-vs-qwen3-vl-8b-benchmarks-vram-guide/)
- [Qwen3-VL Technical Report (arXiv 2511.21631)](https://arxiv.org/abs/2511.21631)
- [Best Open-Weight Vision-Language Models 2026 (Presenc AI)](https://presenc.ai/research/best-open-weight-vision-language-models-2026)
- [OCR & Document AI Leaderboard 2026 (Awesome Agents)](https://awesomeagents.ai/leaderboards/ocr-document-ai-leaderboard/)
- [Best Ollama Vision Models 2026 (Serverman)](https://www.serverman.co.uk/ai/ollama/best-ollama-models-for-vision/)
- [PISA-Bench: multilingual & multimodal VLM evaluation (arXiv 2510.24792)](https://arxiv.org/pdf/2510.24792)
- [Self-hosted VLM comparison: Qwen-VL, Llama 3.2 Vision, Pixtral (GigaGPU)](https://gigagpu.com/self-hosted-vision-language-model-comparison/)
- [Open-source VLM guide (BentoML)](https://www.bentoml.com/blog/multimodal-ai-a-guide-to-open-source-vision-language-models)
- [Mistral OCR 4 launch (VentureBeat)](https://venturebeat.com/data/mistral-launches-ocr-4-turning-document-extraction-into-a-full-enterprise-ai-play)
- [Best open-source LLM for French 2026 (SiliconFlow)](https://www.siliconflow.com/articles/en/best-open-source-LLM-for-French)
- [Q4_K_M vs Q8_0 quantization explained (PromptQuorum)](https://www.promptquorum.com/local-llms/llm-quantization-explained)
- [GGUF quantization guide 2026 (Pristren)](https://pristren.com/blog/gguf-quantization-guide-2026/)
- [Ollama VRAM requirements 2026 (LocalLLM.in)](https://localllm.in/blog/ollama-vram-requirements-for-local-llms)

---

*History: the repo previously used `gemma3:4b`, then briefly `qwen2.5vl:7b`,
before consolidating on `qwen3-vl:8b` (2026), the newer generation that keeps
the OCR/chart lead while bringing French up to par. See the CHANGELOG.*
