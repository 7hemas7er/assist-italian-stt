# Clean-audio benchmark: Italian STT for Assist (6 October 2026)

Question: replace `wyoming-whisper` (faster-whisper `small-int8` on CPU, 4 threads, beam 1, home names in
the prompt)? With what, given that neither NVIDIA Parakeet nor Nemotron declares arm64 support?

Short answer: **yes, with Parakeet TDT 0.6B v3, without changing the image.** The production image,
`rhasspy/wyoming-whisper:latest` (wyoming-faster-whisper 3.6.0), already contains sherpa-onnx and
onnx-asr and can serve Parakeet v3 on an arm64 CPU with two extra arguments. It halves the errors and
takes a command from 1.35 s to 0.08 s. **Nemotron 3.5 streaming: no.** Worse than Parakeet on every set,
loses the first words of short commands, and its only advantage (streaming partials) is useless here.

## What was measured

- **FLEURS it_it test**: 865 sentences, 211 minutes, read by real people (about 14.7 s each). The main
  set. A fixed 200-sentence subset for the slow runs, and a 703-sentence subset without digits to take
  number formatting out of the picture.
- **MLS Italian**: 300 sentences, 75 minutes, audiobooks (Dante included). Stress test only.
- **Synthetic home commands**: 40 commands with the real area and entity names exposed to Assist, each
  spoken by two Italian Piper voices (`paola-medium`, `riccardo-x_low`): 80 files, 3.6 minutes, median
  2.68 s. Synthetic speech is clean, no room, no microphone, and Piper mispronounces some names
  (`led`, camera names). Absolute WER is high for everyone on this set; the ranking is what counts.
- **Production log**: timings only, from the last 7 days of `docker logs wyoming-whisper`, never the text.

WER normalised identically on reference and hypothesis (lower case, punctuation removed, numbers spelled
out in Italian with num2words, apostrophes and hyphens as spaces). RTF = compute time / audio duration.
Greedy / beam 1, one sentence at a time. CPU runs pinned to 4 big cores like production; onnx-asr
cannot be pinned (onnxruntime refuses the affinity) and uses every core.

## FLEURS Italian, 865 sentences (211 min)

| system | where | WER % | WER % no digits (703) | RTF | p50 per sentence |
|---|---|---|---|---|---|
| whisper small int8 (twin of production) | CPU, 4 threads | 7.61 | 7.45 | 0.219 | 2.16 s |
| Parakeet v3 int8, sherpa, **production image** | CPU, 4 threads | 3.81 | 3.52 | 0.020 | 0.28 s |
| Parakeet v3 int8, tboby `wyoming-onnx-asr` | CPU, all cores | 3.90 | 3.73 | 0.056 | 0.68 s |
| Parakeet v3 fp32, NeMo | GPU | 2.70 | 2.64 | 0.0043 | 0.06 s |
| Parakeet v3 q8_0, NeMo-Speech.cpp | GPU | 3.10 | 2.71 | 0.0023 | 0.03 s |
| Nemotron 3.5 streaming, 1120 ms chunks, NeMo | GPU | 4.83 | 3.78 | 0.018 | 0.25 s |
| Nemotron 3.5 streaming, 560 ms chunks, NeMo | GPU | 5.01 | 3.93 | 0.031 | 0.43 s |
| Nemotron 3.5 streaming, 1120 ms, NeMo-Speech.cpp q8_0 | GPU | 4.82 | 3.75 | 0.0075 | 0.11 s |
| whisper large-v3-turbo fp16, transformers | GPU | 2.53 | 2.33 | 0.0127 | 0.18 s |

## FLEURS, 200-sentence subset (48 min)

| system | where | WER % | RTF | p50 |
|---|---|---|---|---|
| whisper small int8, **via Wyoming** in the production image | CPU, 4 threads | 8.27 | 0.186 | 1.88 s |
| whisper small int8, direct (same faster-whisper) | CPU, 4 threads | 8.25 | 0.249 | 2.14 s |
| whisper large-v3-turbo int8, faster-whisper | CPU, 4 threads | 2.72 | 0.425 | 5.82 s |
| Parakeet v3 **fp32**, onnx-asr, **production image** | CPU, all cores | 2.68 | 0.038 | 0.52 s |
| Parakeet v3 int8, sherpa, production image | CPU, 4 threads | 3.99 | 0.020 | 0.28 s |
| Parakeet v3 q8_0, NeMo-Speech.cpp | CPU, 4 cores | 3.22 | 0.113 | 1.58 s |
| Parakeet v3 fp32, NeMo | GPU | 2.66 | 0.0042 | 0.06 s |
| Nemotron 1120 ms, NeMo-Speech.cpp | CPU, 4 cores | 4.72 | 0.148 | 2.06 s |
| Nemotron 1120 ms, NeMo, language `it-IT` | GPU | 5.07 | 0.018 | 0.26 s |
| Nemotron 1120 ms, NeMo, language `auto` | GPU | 5.15 | 0.018 | 0.25 s |
| Nemotron 160 ms, NeMo | GPU | 5.37 | 0.096 | 1.35 s |
| Qwen3-ASR 0.6B int4, production image | CPU, 4 threads | 8.23 | 0.081 | 1.07 s |

## MLS Italian, 300 audiobook sentences (75 min), stress test

| system | WER % | RTF |
|---|---|---|
| whisper large-v3-turbo, GPU | 9.84 | 0.0146 |
| Parakeet v3 fp32, NeMo, GPU | 11.37 | 0.0048 |
| Parakeet v3 fp32, onnx-asr, CPU (production image) | 11.40 | 0.036 |
| Parakeet v3 q8_0, C++, GPU | 11.47 | 0.0024 |
| Parakeet v3 int8, sherpa, CPU (production image) | 13.83 | 0.0205 |
| Nemotron 1120 ms, NeMo, GPU | 15.49 | 0.0188 |
| whisper small int8, CPU (production) | 19.66 | 0.185 |

## Synthetic home commands, 80 files (median 2.68 s)

| system | WER % | voice paola | voice riccardo | p50 per command | p95 |
|---|---|---|---|---|---|
| whisper large-v3-turbo, GPU | 17.24 | 13.30 | 21.18 | 0.089 s | 0.101 s |
| Parakeet v3 fp32, NeMo, GPU | 17.98 | 16.75 | 19.21 | 0.043 s | 0.049 s |
| Parakeet v3 fp32, onnx-asr, CPU (production image) | 18.23 | 17.24 | 19.21 | 0.182 s | 0.251 s |
| **Parakeet v3 int8, sherpa, CPU (production image)** | **18.47** | 18.23 | 18.72 | **0.081 s** | 0.092 s |
| Nemotron 1120 ms, C++, GPU | 27.83 | 19.70 | 35.96 | 0.033 s | 0.040 s |
| whisper small int8 + home names in the prompt (emulated) | 28.33 | 27.09 | 29.56 | 1.488 s | 1.592 s |
| Nemotron 1120 ms, NeMo, GPU | 29.56 | 26.11 | 33.00 | 0.063 s | 0.068 s |
| **whisper small int8, as in production but without the prompt** | **36.21** | 32.02 | 40.39 | **1.348 s** | 1.548 s |
| Nemotron 160 ms, NeMo, GPU | 37.93 | 28.57 | 47.29 | 0.299 s | 0.360 s |

## Production, from its own log (7 days)

22 requests, median audio 3.42 s. From the start of the transcription to the final text: **median
1.29 s**, matching the twin measured on synthetic commands (1.35 s). But **8 requests of 22 took more
than 5 seconds, up to 21.8 s**; in one, 1.75 s of audio produced 20 words in 21 s. The likely cause
(not verified) is faster-whisper's temperature fallback on audio with little speech, in other words
hallucination. Parakeet is a transducer with no temperature fallback: its p95 on commands is 0.09 s.

## Memory

| system | memory |
|---|---|
| whisper small, production container | 436 MiB idle, 1.39-1.46 GiB under load |
| Parakeet int8 sherpa (container) | 1.23-1.62 GiB |
| Parakeet fp32 onnx-asr (container) | 2.55 GiB on commands and MLS, 4.85 GiB on long FLEURS sentences |
| Qwen3-ASR int4 (container) | 2.91 GiB |
| NeMo on GPU, torch allocator peak | 4.74 GiB Parakeet, 4.82 GiB Nemotron; turbo 1.58 GiB |

Start-up: NeMo 20-23 s (Parakeet) and 41-46 s (Nemotron, unpacks the `.nemo`); NeMo-Speech.cpp
0.03-0.31 s; Wyoming servers ready in 2-8 s.

## Conclusions

- **Replace `wyoming-whisper`'s model with Parakeet v3 in the same image.** FLEURS 7.61% to 3.81%, MLS
  19.66% to 13.83%, synthetic commands 36.2% to 18.5%. It also beats whisper small *with* home names in
  the prompt (28.3%), which was the advantage production relied on. 1.35 s to 0.08 s per command, no
  more 20-second queues. No new container, nothing to change in Home Assistant.
- **fp32 via onnx-asr when errors still bite**: 2.68% against 3.99% on FLEURS-200, 11.4% against 13.8%
  on MLS. Costs 1.1-3.4 GB more RAM than whisper small under load. (The live test a few days later
  showed that on real far-field speech fp32 is not a refinement but the difference between working
  and not working.)
- **Nemotron 3.5 streaming does not pay.** 4.83% on FLEURS, 28-42% on short commands, loses the first
  words with 160 ms chunks; the first token still arrives 1.5-2 s after speech starts, and no Wyoming
  wrapper exists.
- **The GPU is not needed.** Parakeet fp32 on CPU has the same WER as NeMo on GPU (2.68% vs 2.66%);
  the GPU buys only latency, 0.04 s against 0.08-0.18 s. The most accurate system overall is whisper
  large-v3-turbo (2.53%), but on CPU it takes 5.8 s per sentence and there is no arm64 Wyoming path
  on GPU: faster-whisper has no CUDA ctranslate2 for aarch64, and the GPU images of tboby are amd64 only.
- **Qwen3-ASR (already in the image) improves nothing**: 8.23%, like whisper small. It does accept the
  home names as context, which Parakeet does not.

## Traps worth knowing

- **The int8 quantisation of Parakeet costs one WER point, the q8_0 of NeMo-Speech.cpp half a point**:
  fp32 2.70%, q8_0 3.10%, int8 ONNX 3.81-3.90%.
- **The maintainers' note that Parakeet v3 "claims other languages but does not work" does not hold for
  Italian**: on 865 sentences not one came out in another language; the worst is 44% (Indian proper names).
- **The Wyoming image does not slow whisper down.** Same faster-whisper, identical transcripts in 196
  of 200 sentences and 80 of 80 commands; the timing difference is noise.
- **tboby's wrapper adds nothing**: same Parakeet int8, but onnxruntime without a thread cap, 2.8 times
  slower than sherpa pinned to 4 threads. It cannot be pinned with `--cpuset-cpus`. The same applies
  to `--stt-library onnx-asr` in the production image.
- **The `--hass-*` options do not break sherpa**: with a fake token and an unreachable address the
  server warns and transcribes normally. With sherpa the names are not used.
- **The official NeMo container is not an ASR container as shipped**: NeMo is present as source but not
  installed, cuDNN is mismatched between torch and apt, and some directories lack the execute bit for
  non-root users. All three needed an overlay image before any ASR ran.
