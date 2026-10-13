import json, re, collections
c = json.load(open(r'C:\Users\Admin\pxrt_dev\px_pipeline\corpus.json', encoding='utf-8'))
# class -> base
base = {}
for k, s in c.items():
    for m in re.finditer(r'^\s*(\w+)\s*:\s*(\w+)\s*;', s, re.M):
        base.setdefault(m.group(1), m.group(2))
SOFT = {'CGObject', 'CMine', 'COilDrum', 'CCrate', 'CGas', 'CFire', 'CArrow', 'CCanister', 'CCross', 'CMissile', 'CFlame', 'CSmoke', 'CCloud'}
def root(n):
    seen = set()
    while n in base and n not in seen:
        seen.add(n); n = base[n]
    return n
res = {'with_super': [], 'no_super': []}
for k, s in c.items():
    for m in re.finditer(r'void\s+(\w+)::Message\s*\([^)]*\)\s*\{', s):
        cls = m.group(1)
        if cls not in base:
            continue
        r = root(cls)
        if r not in SOFT:
            continue
        # body: brace matching
        i = m.end(); depth = 1
        while i < len(s) and depth:
            if s[i] == '{': depth += 1
            elif s[i] == '}': depth -= 1
            i += 1
        body = s[m.end():i]
        has = re.search(r'\bsuper\b', body) is not None
        res['with_super' if has else 'no_super'].append((k, cls, r, len(body)))
print('with super', len(res['with_super']), 'no super', len(res['no_super']))
for x in res['no_super'][:40]:
    print(x)
