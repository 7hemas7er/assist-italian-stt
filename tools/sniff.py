"""Passive capture of Wyoming STT requests on :10300, run inside the network namespace of the
wyoming-whisper container (docker run --network container:wyoming-whisper --cap-add NET_RAW ...).
It records what Home Assistant sends and what comes back, so you can replay real far-field audio
against other recognisers. Record only your own voice, tell everyone in the room, delete the WAVs
when done. It reassembles the TCP streams and writes one WAV + one JSON (levels, clipping, text) per request."""
import socket, struct, time, json, wave, os, sys, math, audioop
OUT = sys.argv[1]; PORT = 10300
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3)); s.settimeout(1.0)
flows = {}

def parse_events(buf):
    evs, i = [], 0
    while True:
        j = buf.find(b"\n", i)
        if j < 0: break
        try: hdr = json.loads(buf[i:j])
        except Exception: break
        i = j + 1
        data = hdr.get("data") or {}
        dl, pl = hdr.get("data_length") or 0, hdr.get("payload_length") or 0
        if dl:
            try: data = {**data, **json.loads(buf[i:i+dl])}
            except Exception: pass
            i += dl
        payload = buf[i:i+pl]; i += pl
        evs.append((hdr.get("type"), data, payload))
    return evs

def assemble(segs, isn):
    if not segs: return b""
    base = isn if isn is not None else min(segs)
    out = bytearray(); nxt = base
    for seq in sorted(segs, key=lambda q: (q - base) & 0xffffffff):
        d = segs[seq]; off = (seq - nxt) & 0xffffffff
        if off > 0x7fffffff:
            skip = (nxt - seq) & 0xffffffff
            if skip >= len(d): continue
            d = d[skip:]
        elif off: break
        out += d; nxt = (nxt + len(d)) & 0xffffffff
    return bytes(out)

def finish(key, f):
    c2s = parse_events(assemble(f["c2s"], f["isn"].get("c2s"))); s2c = parse_events(assemble(f["s2c"], f["isn"].get("s2c")))
    fmt = {}; audio = bytearray(); lang = None
    for t, d, p in c2s:
        if t in ("audio-start", "audio-chunk"): fmt = {k: d.get(k, fmt.get(k)) for k in ("rate", "width", "channels")}
        if t == "audio-chunk": audio += p
        if t == "transcribe": lang = d.get("language")
    text = next((d.get("text") for t, d, p in s2c if t == "transcript"), None)
    if not audio and text is None: return
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(f["t0"]))
    rate, width, ch = fmt.get("rate") or 16000, fmt.get("width") or 2, fmt.get("channels") or 1
    a = bytes(audio)
    dur = len(a) / float(rate * width * ch) if a else 0.0
    rms = audioop.rms(a, width) if a else 0; peak = audioop.max(a, width) if a else 0
    full = float(2 ** (8 * width - 1)); clip = sum(1 for k in range(0, len(a) - width + 1, width) if abs(int.from_bytes(a[k:k+width], "little", signed=True)) >= full - 2) if a else 0
    db = lambda v: round(20 * math.log10(v / full), 1) if v else None
    if a:
        with wave.open(os.path.join(OUT, stamp + ".wav"), "wb") as w:
            w.setnchannels(ch); w.setsampwidth(width); w.setframerate(rate); w.writeframes(a)
    meta = {"stamp": stamp, "lang": lang, "rate": rate, "dur_s": round(dur, 2), "rms_dbfs": db(rms),
            "peak_dbfs": db(peak), "clipped_samples": clip, "prod_text": text, "conn_s": round(f["last"] - f["t0"], 2)}
    json.dump(meta, open(os.path.join(OUT, stamp + ".json"), "w"), ensure_ascii=False)
    print(json.dumps(meta, ensure_ascii=False), flush=True)

while True:
    try:
        pkt = s.recv(262144)
        if len(pkt) < 34 or pkt[12:14] != b"\x08\x00": raise socket.timeout
        ip = pkt[14:]; ihl = (ip[0] & 15) * 4
        if ip[9] != 6: raise socket.timeout
        src, dst = socket.inet_ntoa(ip[12:16]), socket.inet_ntoa(ip[16:20])
        tot = struct.unpack("!H", ip[2:4])[0]; tcp = ip[ihl:tot]
        sp, dp, seq = struct.unpack("!HHI", tcp[:8]); flags = tcp[13]; doff = (tcp[12] >> 4) * 4
        data = tcp[doff:]
        if dp == PORT: key, d = (src, sp), "c2s"
        elif sp == PORT: key, d = (dst, dp), "s2c"
        else: raise socket.timeout
        now = time.time()
        f = flows.setdefault(key, {"c2s": {}, "s2c": {}, "isn": {}, "t0": now, "last": now})
        if flags & 0x02: f["isn"][d] = (seq + 1) & 0xffffffff
        if data: f[d][seq] = bytes(data)
        f["last"] = now
        if flags & 0x05: f["closing"] = now
    except socket.timeout:
        pass
    now = time.time()
    for key in [k for k, f in flows.items() if (f.get("closing") and now - f["closing"] > 0.5) or now - f["last"] > 15]:
        try: finish(key, flows[key])
        except Exception as e: print("error", key, e, flush=True)
        del flows[key]
