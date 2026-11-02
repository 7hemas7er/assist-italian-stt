# Italian speech-to-text for Home Assistant Assist

What it took to make a local Italian voice assistant understand commands spoken from the other side
of the room, with measurements: 14 recogniser configurations on 1,245 real sentences and 80 synthetic
commands, then real far-field speech from an ESP32-S3 satellite. Everything runs on CPU, inside the
stock `rhasspy/wyoming-whisper` image, with no change on the Home Assistant side.

**Result**: NVIDIA Parakeet TDT 0.6B v3 in fp32, served by the onnx-asr backend that the image
already contains, replaces faster-whisper `small-int8`. Errors halve on read speech (WER 7.6% to
2.7%), a command is transcribed in 0.2 s instead of 1.3 s, and on real speech 5 m from the satellite
it goes from 0 of 8 commands understood to 5 of 8; with Italian aliases on the entities, 4 of 4.

## Use it

```bash
git clone https://github.com/7hemas7er/assist-italian-stt
cd assist-italian-stt
bash recreate.sh            # starts wyoming-whisper on :10300 with Parakeet v3 fp32
```

Then in Home Assistant point the Wyoming integration at `<host>:10300` and select it as the
speech-to-text of your Assist pipeline. The model (2.4 GB) downloads on first start. Environment
variables: `STT_LIBRARY` (`onnx-asr` default, or `sherpa` for the int8 model), `STT_MODEL`,
`STT_LANGUAGE` (`it`), `STT_PORT`, `DATA_DIR`. `HASS_API` and a `hass_token` file enable the
home-name hints, which only the faster-whisper models use.

Memory: about 2.4 GB for fp32, 1.2 GB for int8. If RAM is tight use int8, but read the live test
first: on far-field speech int8 understood 1 command of 8 where fp32 understood 5.

## The three findings that matter

1. **Quantisation is not free on real microphones.** On clean audio Parakeet int8 and fp32 were
   level. On speech from 5 m away, reverberant and quiet, int8 collapsed (2 of 15 live commands) and
   fp32 held (9 of 16). Benchmarks on read speech do not predict this. [docs/live-test.md](docs/live-test.md)
2. **Aliases beat models.** The light was called "Led sala": an English word that Parakeet turns into
   "le", "letto", "Sara". Adding Italian aliases (Luce sala, Luci salone...) made 4 of 4 commands work,
   resolved by Home Assistant's local intent matcher with no LLM call at all.
3. **The satellite lies about its gain.** On the Waveshare ESP32-S3 audio board the "Gain Factor" and
   "Noise Suppression" numbers shown by Home Assistant are template values without `optimistic` and
   without a boot action: they apply only when you change them, after a reboot the firmware default
   is back, and HA keeps showing the old value. At the real gain of 32 the audio clips (~1,700
   clipped samples per sentence). Set them again after every satellite reboot, or fix the firmware.

## Measurements

- [docs/benchmark-clean-audio.md](docs/benchmark-clean-audio.md): FLEURS (865 sentences), MLS (300),
  synthetic commands (80); whisper small/turbo, Parakeet v3 (fp32, int8, q8_0), Nemotron 3.5
  streaming, Qwen3-ASR; CPU and GPU; memory, start-up, production log. Why Nemotron streaming does
  not pay and why the GPU is not needed.
- [docs/live-test.md](docs/live-test.md): four rounds of real speech, the same audio replayed through
  seven recognisers, the satellite gain experiments, what `--vad-clip` and `--vad-filter` do to
  distant speech, the aliases.
- [docs/latency-and-tts.md](docs/latency-and-tts.md): where the time goes between the end of speech
  and the answer, preloading the LLM at boot, stopping it from inventing the date, and Piper
  `serena-high` against `serena-medium` (4.5 times slower for a small gain).

## Reproduce the live test

```bash
# 1. capture what HA sends, inside the STT container's network namespace (your voice, with consent)
docker run --rm --network container:wyoming-whisper --cap-add NET_RAW \
  -v "$PWD:/w" --entrypoint python3 rhasspy/wyoming-whisper -I /w/tools/sniff.py /w/rec
# 2. write rec/<stamp>.wav references into refs.tsv (see refs.example.tsv)
# 3. replay the same audio through the seven configurations and score them
tools/runall.sh refs.tsv
```

`tools/score.py` prints WER, exact matches and median time per configuration; `-v` shows every
transcript. Delete `rec/` when you are done.

## Notes

- The image is arm64 and amd64; everything here was measured on an arm64 host. The sherpa and
  onnx-asr backends are the two extra arguments that unlock Parakeet; `--stt-library onnx-asr` cannot
  be pinned to a CPU set (onnxruntime refuses the affinity) and uses every core for a few tenths of a
  second per command.
- Parakeet v3 cannot be forced to Italian: on very short or poor audio it answers in English or
  Portuguese. Better audio makes it rare; the aliases make it irrelevant for the commands you use most.
- A timer ringing on the satellite is a firmware announcement: `media_stop` does not stop it. Say
  "Stop", or wait 15 minutes.
- Check the list of entities exposed to Assist now and then. Fourteen inverter control switches had
  crept in; a misheard command could have toggled them.

MIT licence. Measurements from October 2026; numbers will drift with new model and image releases.
