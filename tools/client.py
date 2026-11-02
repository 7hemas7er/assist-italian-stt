"""Send a WAV to a Wyoming STT server and print the transcript (for tests and the offline comparison)."""
import asyncio, sys, wave, time
from wyoming.client import AsyncTcpClient
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.asr import Transcribe, Transcript
async def run(host, port, path, lang="it"):
    with wave.open(path) as w:
        rate, width, ch, frames = w.getframerate(), w.getsampwidth(), w.getnchannels(), w.readframes(w.getnframes())
    t0 = time.perf_counter()
    async with AsyncTcpClient(host, port) as c:
        await c.write_event(Transcribe(language=lang).event())
        await c.write_event(AudioStart(rate=rate, width=width, channels=ch).event())
        step = 1024 * width * ch
        for i in range(0, len(frames), step):
            await c.write_event(AudioChunk(rate=rate, width=width, channels=ch, audio=frames[i:i+step]).event())
        await c.write_event(AudioStop().event())
        while True:
            e = await c.read_event()
            if e is None: return None, time.perf_counter() - t0
            if Transcript.is_type(e.type): return Transcript.from_event(e).text, time.perf_counter() - t0
if __name__ == "__main__":
    host, port = sys.argv[1], int(sys.argv[2])
    for p in sys.argv[3:]:
        text, dt = asyncio.run(run(host, port, p))
        print(f"{p}\t{dt:.2f}s\t{text}", flush=True)
