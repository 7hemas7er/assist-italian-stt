#!/bin/bash
# Offline comparison of Wyoming recognisers on the same recorded WAVs: one temporary server at a
# time on 127.0.0.1:10320, inside the stock rhasspy/wyoming-whisper image.
# Usage: eval.sh <refs.tsv> <config-name> [server arguments...]
#   refs.tsv: <stamp><TAB><reference text>, one per line; audio is rec/<stamp>.wav
#   Results land in eval/<config-name>.tsv (file, seconds, transcript); score them with score.py.
set -u
V="$(cd "$(dirname "$0")/.." && pwd)"; REFS=$1; NAME=$2; shift 2
mkdir -p "$V/eval" "$V/models"
docker rm -f stt-eval >/dev/null 2>&1
docker run -d --name stt-eval -p 127.0.0.1:10320:10320 -v "$V/models:/models" \
  rhasspy/wyoming-whisper --uri tcp://0.0.0.0:10320 --data-dir /models --download-dir /models "$@" >/dev/null
for i in $(seq 1 600); do docker logs stt-eval 2>&1 | grep -q 'Ready' && break; docker ps -q -f name=stt-eval | grep -q . || break; sleep 1; done
if ! docker logs stt-eval 2>&1 | grep -q Ready; then echo "$NAME: server did not start"; docker logs stt-eval 2>&1 | tail -5; docker rm -f stt-eval >/dev/null; exit 1; fi
files=$(cut -f1 "$REFS" | sed 's|^|/w/rec/|; s|$|.wav|' | tr '\n' ' ')
# one warm-up pass, then the measured one
docker run --rm --network host --entrypoint /usr/src/.venv/bin/python3 -v "$V:/w" rhasspy/wyoming-whisper -I /w/tools/client.py 127.0.0.1 10320 "/w/rec/$(head -1 "$REFS" | cut -f1).wav" >/dev/null
docker run --rm --network host --entrypoint /usr/src/.venv/bin/python3 -v "$V:/w" rhasspy/wyoming-whisper -I /w/tools/client.py 127.0.0.1 10320 $files > "$V/eval/$NAME.tsv"
mem=$(docker stats --no-stream --format '{{.MemUsage}}' stt-eval | cut -d/ -f1)
docker rm -f stt-eval >/dev/null
echo "$NAME done (mem $mem)"
