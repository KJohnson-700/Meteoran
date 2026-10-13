import io, re
s = io.open('docs/stock-pairs.html', encoding='utf-8').read()
body = re.sub(r'<style.*?</style>', '', s, flags=re.S)
text = re.sub(r'<[^>]+>', ' ', body)
text = re.sub(r'\s+', ' ', text)

# Language that renders a verdict rather than reporting a measurement.
BAD = [
    r'\d+(\.\d+)?x\b', r'\bworse\b', r'\bbest\b', r'\bbest-performing\b',
    r'\bthe finding\b', r'\bverdict\b', r'\btransfer\b', r'\bcalibrat',
    r'\bgates?\b', r'\b111,838\b', r'\bconclusion\b', r'\bthis is why\b',
    r'\bshould\b', r'\bavoid\b', r'\bdon\'?t\b', r'\bbottom decile\b',
    r'\bpays?\b(?! )', r'\bstop(s|ped)? covering\b',
]
hits = []
for pat in BAD:
    for m in re.finditer(pat, text, re.I):
        hits.append((pat, text[max(0, m.start()-70):m.end()+70].strip()))
print('EDITORIAL LANGUAGE FOUND:', len(hits))
for p, ctx in hits:
    print('  [%s] ...%s...' % (p, ctx))