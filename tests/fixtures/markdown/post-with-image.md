# Why we standardised on `pywhispercpp` for captions

We tried five Whisper backends before settling on `pywhispercpp`. The deciding
factor was the offline footprint: no GPU dependency, no Python ABI tied to a
specific CUDA build, and predictable memory use on the laptops our writers
actually use.

![Bar chart comparing throughput across five Whisper backends, with pywhispercpp leading on CPU-only runs](../images/chart-bar.png)

The chart above shows median throughput across a thousand thirty-second clips.
`pywhispercpp` wins on the CPU-only column by a wide margin, which matches our
deployment target: editorial laptops, not the GPU cluster.

## What we kept from the other backends

- Faster-Whisper's segment cleanup heuristics.
- The `--vocab` glossary biasing pattern from whisper.cpp's own CLI.
- The output formats: WebVTT, SRT, and plain transcript with paragraph breaks.
