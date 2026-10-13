import re, glob, collections, json, os
cls = json.load(open('px/classes.json'))
# field name -> classes declaring it
own = collections.defaultdict(list)
for c, d in cls.items():
    flds = d.get('fields') if isinstance(d, dict) else None
    if flds is None:
        continue
    for f in (flds if isinstance(flds, list) else flds.keys()):
        n = f if isinstance(f, str) else f.get('name')
        own[n].append(c)
print('classes:', {c: len((d.get('fields') or [])) for c, d in cls.items() if isinstance(d, dict)})
cnt = collections.Counter(); pk = collections.defaultdict(set)
other = collections.Counter()
for f in glob.glob('testout/lua/*/*.lua'):
    pkg = os.path.basename(os.path.dirname(f))
    s = open(f, encoding='utf-8', errors='replace').read()
    for m in re.findall(r'[\w\)\]]\.([A-Z]\w*)\b', s):
        if m in own:
            cnt[m] += 1; pk[m].add(pkg)
        else:
            other[m] += 1
print('== engine fields used', len(cnt))
print(' '.join('%s(%s):%d/%d' % (k, ','.join(own[k]), v, len(pk[k])) for k, v in cnt.most_common()))
print('== engine fields unused', [k for k in own if k not in cnt])
print('== other dotted caps (top 150)')
print(' '.join('%s:%d' % kv for kv in other.most_common(150)))
