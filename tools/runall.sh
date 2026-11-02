#!/bin/bash
# The seven configurations compared in docs/live-test.md, all from the stock image.
V="$(cd "$(dirname "$0")/.." && pwd)"; R="${1:-$V/refs.tsv}"
"$V/tools/eval.sh" "$R" parakeet-int8          --stt-library sherpa --model sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8 --language it
"$V/tools/eval.sh" "$R" parakeet-int8-vadclip  --stt-library sherpa --model sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8 --language it --vad-clip
"$V/tools/eval.sh" "$R" whisper-small-int8     --stt-library faster-whisper --model small-int8 --language it --beam-size 1
"$V/tools/eval.sh" "$R" parakeet-fp32          --stt-library onnx-asr --model nemo-parakeet-tdt-0.6b-v3 --language it
"$V/tools/eval.sh" "$R" parakeet-fp32-vadclip  --stt-library onnx-asr --model nemo-parakeet-tdt-0.6b-v3 --language it --vad-clip
"$V/tools/eval.sh" "$R" whisper-turbo          --stt-library faster-whisper --model turbo --language it --compute-type int8 --beam-size 5 --cpu-threads 8
"$V/tools/eval.sh" "$R" whisper-turbo-vad      --stt-library faster-whisper --model turbo --language it --compute-type int8 --beam-size 5 --cpu-threads 8 --vad-filter
python3 -I "$V/tools/score.py" "$R" "$V/eval" -v
