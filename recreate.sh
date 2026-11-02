#!/usr/bin/env bash
# Run the Wyoming speech-to-text server for Home Assistant Assist with NVIDIA Parakeet
# TDT 0.6B v3 (fp32, onnx-asr) inside the stock rhasspy/wyoming-whisper image.
# No new image: the image already ships sherpa-onnx and onnx-asr next to faster-whisper.
#
# Usage:
#   export HASS_API=http://homeassistant.local:8123/api     # optional, for home-name hints
#   echo "<long-lived token>" > ./hass_token && chmod 600 ./hass_token   # optional
#   bash recreate.sh
#
# The token is never printed. Note: with sherpa and onnx-asr the home-name hints are
# accepted but not used by the recogniser; they only matter for faster-whisper models.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${DATA_DIR:-$DIR/data}"
TOKEN_FILE="${HASS_TOKEN_FILE:-$DIR/hass_token}"
HASS_API="${HASS_API:-}"
MODEL="${STT_MODEL:-nemo-parakeet-tdt-0.6b-v3}"      # fp32 via onnx-asr (best on far-field speech)
LIBRARY="${STT_LIBRARY:-onnx-asr}"                     # or: sherpa + sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
LANG_CODE="${STT_LANGUAGE:-it}"
PORT="${STT_PORT:-10300}"

mkdir -p "$DATA"
HASS_ARGS=()
if [[ -n "$HASS_API" && -s "$TOKEN_FILE" ]]; then
  chmod 600 "$TOKEN_FILE"
  HASS_ARGS=(--hass-token "$(tr -d '[:space:]' < "$TOKEN_FILE")"
             --hass-api "$HASS_API"
             --hass-refresh-seconds 300
             --hass-prompt-max-tokens 200
             --hass-prompt-timeout 1.0)
  echo "home-name hints: on (token read from $TOKEN_FILE)"
else
  echo "home-name hints: off (set HASS_API and $TOKEN_FILE to enable)"
fi

docker rm -f wyoming-whisper >/dev/null 2>&1 || true
docker run -d --name wyoming-whisper \
  --restart unless-stopped \
  -p "$PORT:10300" \
  -v "$DATA:/data" \
  --health-cmd 'python3 -c "import socket; socket.create_connection((\"127.0.0.1\",10300),3).close()"' \
  --health-interval 30s --health-timeout 5s --health-retries 3 --health-start-period 60s \
  rhasspy/wyoming-whisper:latest \
  --uri tcp://0.0.0.0:10300 --stt-library "$LIBRARY" --model "$MODEL" --language "$LANG_CODE" \
  --data-dir /data --download-dir /data \
  "${HASS_ARGS[@]}" >/dev/null
echo "wyoming-whisper started on :$PORT with $LIBRARY / $MODEL"
