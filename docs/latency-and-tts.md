# Where the time goes, and the Piper voices (7 October 2026)

Measured before touching anything, with the LLM already in memory.

| stage | time | note |
|---|---|---|
| end of speech | | satellite on `aggressive` VAD, the fastest setting |
| recognition (Parakeet, CPU) | ~0.1 s | [benchmark-clean-audio.md](benchmark-clean-audio.md) |
| commands HA resolves itself | almost nothing | `prefer_local_intents: true`, no LLM call |
| LLM, direct answer | 0.3-0.4 s | one call |
| LLM, command through a tool | 0.8-1.1 s | two calls: pick the action, then answer |
| Piper `it_IT-serena-high` | see below | add-on on the HA host |

The real slowdowns:

- **Model reload after a reboot: 5-15 s** on the first command. Fixed with a small systemd user unit
  that waits for Ollama, checks free memory, and loads the same model with the same `num_ctx` and
  `keep_alive: -1` that Home Assistant uses. If the options match, HA finds the loaded instance and
  does not load a second one (verified: first question after a reboot, 1.28 s and 0.31 s, no cold start).
- **GPU busy with other work: 3-5 times slower.**
- **The LLM invented the date.** "What day is it?" was answered "5 April 2025" with one call and no
  tool. One line added to the conversation agent's prompt: *"For the time, the date or the day of the
  week always call the GetDateTime tool and answer with its result; never make them up."* After that,
  6 of 7 date questions right and all through the tool; the seventh asks for clarification instead of
  inventing.

## Piper: high against medium

`piper-tts` 1.8.0, onnxruntime 1.30, CPU. Three typical sentences, median of 5 runs after warm-up.
Time to first audio = when the voice starts speaking.

| voice | all cores | 4 cores (`taskset 0-3`) | RTF (all / 4 cores) |
|---|---|---|---|
| `it_IT-serena-high` (114 MB) | 0.24-0.39 s | 0.41-0.74 s | 0.12-0.15 / 0.23-0.25 |
| `it_IT-serena-medium` (64 MB) | 0.05-0.08 s | 0.10-0.17 s | 0.03 / 0.055 |
| `it_IT-paola-medium` (64 MB) | 0.05-0.08 s | | 0.03 |

`high` is about **4.5 times slower** than `medium` of the same voice. On a small x86 HA host, where
Piper usually runs as an add-on, `serena-high` sits above the 0.4-0.7 s measured on 4 cores. The
pipeline now uses `it_IT-serena-medium`: same voice, slightly less defined, a response that starts
before you notice.
