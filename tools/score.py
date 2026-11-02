"""WER and exact matches per config: compares eval/<config>.tsv with the reference file (stamp<TAB>text)."""
import sys, re, glob, os, unicodedata
refs = dict(l.rstrip('\n').split('\t') for l in open(sys.argv[1], encoding='utf-8') if l.strip())
def norm(t):
    t = (t or '').lower().replace("’", "'")
    t = re.sub(r"['\-]", ' ', t); t = re.sub(r"[^\w\s]", ' ', t)
    return t.split()
def ed(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j-1] + 1, p + (x != y))
    return d[len(b)]
rows = []
for f in sorted(glob.glob(os.path.join(sys.argv[2], '*.tsv'))):
    name = os.path.basename(f)[:-4]; err = tot = ok = 0; times = []; outs = []
    for line in open(f, encoding='utf-8'):
        p, dt, *txt = line.rstrip('\n').split('\t'); txt = txt[0] if txt else ''
        stamp = os.path.basename(p)[:-4]
        if stamp not in refs: continue
        r, h = norm(refs[stamp]), norm(txt); e = ed(r, h)
        err += e; tot += len(r); ok += (e == 0); times.append(float(dt[:-1])); outs.append(txt)
    times.sort()
    rows.append((err / tot if tot else 1, name, ok, len(times), times[len(times)//2] if times else 0, outs))
for wer, name, ok, n, t50, outs in sorted(rows):
    print(f"{name:<24} WER {wer*100:5.1f}%  exact {ok}/{n}  p50 {t50:.2f}s")
    if '-v' in sys.argv: print('    ' + ' | '.join(outs))
