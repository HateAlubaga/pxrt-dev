import json, re, os, glob, collections, sys
c = json.load(open('px/classes.json'))
fields = {}
for cn, v in c.items():
    for f in v.get('fields', []):
        fields.setdefault(f[0], []).append(cn)
fm = {}
for it in json.load(open('re/fieldmap2.json'))['items']:
    fm[it['px_name'].split('.')[-1]] = it
ini = open(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\wkJellyWorm.ini', encoding='latin-1').read()
act = [l.split('=')[0] for l in ini.splitlines() if l.endswith('=1') and '_' in l.split('=')[0] and not l.startswith(';')]
if len(sys.argv) > 1:
    act = sys.argv[1:]
files = []
libs = set()
for p in act + ['darkness2016']:
    d = os.path.join('testout/lua', p)
    if not os.path.isdir(d):
        continue
    pc = json.load(open(os.path.join(d, 'pxchunks.json')))
    files += [os.path.join(d, x) for x in pc['chunks']]
    libs.update(pc['libs'])
for l in libs:
    files += glob.glob('testout/lua/@lib/%s/*.lua' % l)
cnt = collections.Counter()
for f in files:
    s = open(f, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'\.([A-Za-z_]\w*)', s):
        cnt[m.group(1)] += 1
print('files', len(files))
mapped, unm = [], []
for n, k in cnt.most_common():
    if n in fields:
        (mapped if n in fm else unm).append((n, k, fields[n]))
print('MAPPED', ' '.join('%s:%d' % (n, k) for n, k, _ in mapped))
print('UNMAPPED engine fields used', ' '.join('%s:%d[%s]' % (n, k, ','.join(cl)) for n, k, cl in unm))
