# Live test: real voice, 5 m from the satellite (8 October 2026)

All earlier measurements ([benchmark-clean-audio.md](benchmark-clean-audio.md)) used clean audio:
FLEURS read speech and synthetic commands from Piper voices. The production log said something else.
Recent transcripts of "Accendi Led Sala" (turn on the living-room LED) included "Spini Led Sala",
"Spino", "Me see" and "I change the letters".

## Method

- **Passive capture, for the test only.** A container in the same network namespace as
  `wyoming-whisper` reads the Wyoming traffic on :10300 and saves the audio Home Assistant sends and the
  text that comes back ([`tools/sniff.py`](../tools/sniff.py)). The production path is untouched. The
  WAV files were deleted at the end of the evening.
- **Four rounds** of 8 fixed sentences, spoken by one person about 5 m from a Waveshare ESP32-S3
  audio satellite: turn the living-room LED on and off, what time is it, temperature in the living room,
  a two-minute timer and its cancellation, the state of the gate, tomorrow's weather.
- **Offline comparison on the same audio**: temporary Wyoming servers from the same image, one at a
  time on 127.0.0.1:10320 ([`tools/eval.sh`](../tools/eval.sh), [`tools/client.py`](../tools/client.py),
  [`tools/score.py`](../tools/score.py)).

## Round 1: the original settings, the same audio given to 7 recognisers

Audio: average -27 dBFS, peaks at -3 dBFS, no clipped samples.

| recogniser | exact sentences | WER | time per command |
|---|---|---|---|
| **Parakeet v3 fp32 (onnx-asr)** | **5/8** | **21.9%** | 0.18 s |
| whisper large-v3-turbo int8, beam 5, 8 threads | 4/8 | 21.9% | 4.27 s |
| Parakeet v3 fp32 + `--vad-clip` | 4/8 | 31.2% | 0.17 s |
| Parakeet v3 int8 (sherpa), **production at the time** | 1/8 | 46.9% | 0.08 s |
| Parakeet v3 int8 + `--vad-clip` | 1/8 | 62.5% | 0.07 s |
| whisper small int8 (production until the day before) | 0/8 | 81.2% | 1.89 s |
| whisper large-v3-turbo + `--vad-filter` | 0/8 | 93.8% | drops the speech |

## Rounds 2 to 4: live, changing the satellite gain

| round | recogniser | satellite gain | noise suppression | audio | exact | LED actually switched |
|---|---|---|---|---|---|---|
| 1 | int8 | unknown (firmware value) | unknown | -27 dBFS, peaks -3 | 1/8 | no |
| 2 | int8 | 32 (set from HA) | 0 | **clipping**: ~1,700 clipped samples per sentence | 1/7 (fp32 offline 3/7) | no |
| 3 | **fp32** | 4 | 0 | slight clipping, ~150 samples | **6/8** | **yes** (on and off) |
| 4 | **fp32** | 2 | 0 | clean, -25 dBFS, 2 samples | 3/8 | no |

Live: fp32 **9 of 16**, int8 **2 of 15**. The difference between rounds 3 and 4 is mostly chance
(8 sentences per round): Parakeet normalises the level itself, gain only matters until it clips.

## What follows

1. **Parakeet's int8 quantisation collapses on real speech**: distant, reverberant, from the satellite
   microphone. On October's clean audio int8 and fp32 were level on commands; here 1 of 8 against 5 of 8
   on the same audio. Production now runs `--stt-library onnx-asr --model nemo-parakeet-tdt-0.6b-v3`:
   2.35 GB of RAM instead of 1.2, about 0.2 s per command.
2. **whisper large-v3-turbo is not an option on CPU**: accuracy close to fp32, 4.3 s per command.
3. **Silence filters make it worse**: `--vad-clip` cuts the start of words, whisper's `--vad-filter`
   discards distant speech altogether.
4. **"Led" is the weak spot**: an English word, it becomes "le", "l'edà", "Sara", "letto". Home
   Assistant's intent matcher does not rescue "Accendi le sala" or "Spigli Luci Sala". All evening the
   light only switched when the text was exactly "Led Sala". Fix: Italian aliases on the entity (below).
5. **Parakeet v3 cannot be pinned to Italian**: on short commands or poor audio it answers in English or
   Portuguese ("Chevrolets, one" for "Che ore sono", "Que tempo para..."). It happens less with better audio.
6. **The satellite does not apply gain and noise suppression at boot**, although HA shows them (see the
   README). Left live at gain 2, suppression 0.

## Also found

- A timer ringing on the satellite **cannot be stopped from HA**: it is a firmware announcement,
  `media_stop` does not touch it. It stops on "Stop", on a satellite reboot, or by itself after 15 minutes.
- When the model asks a question the satellite reopens the microphone: if nobody speaks, Parakeet
  transcribes the silence as English ("Okay, now", "Yeah, well") and the model receives a meaningless
  sentence.

## Aliases instead of a better model

The light was only named "Led sala RGBW light 0". Adding the aliases **Led sala, Luce sala, Luci sala,
Luce salone, Luci salone** (keeping the original name) changed everything: 4 of 4 spoken commands
("Accendi luce sala", "Spegni luce sala", "Accendi luci del salone", "Spegni led sala") were transcribed
correctly and executed within a second of the text, **with no LLM call**: Home Assistant's local intent
matcher resolves them (`prefer_local_intents`). With long or English names in Assist, always add
Italian aliases.

## Exposure hygiene

The entities exposed to Assist had crept from 41 to 68. Fourteen of them were switches of the solar
inverter's control unit (ESS charge schedules, peak shaving, relays, two of them simply called
"State"): a misheard command, or a model error, could have toggled them. Removed from the `conversation`
exposure, now 54. Worth checking every few months.
