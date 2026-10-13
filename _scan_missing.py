"""Static scan: method names called through mc(o, "Name") and builtins F.Name used by transpiled packages that no
runtime file and no script defines. Prints name, number of packages, examples."""
import os, re, glob, collections
DEV = r'C:\Users\Admin\pxrt_dev'
LUA = os.path.join(DEV, 'px_pipeline', 'testout', 'lua')
rt = ''.join(open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(DEV, 'pxrt_*.lua')))
rt_def = set(re.findall(r'\.(\w+)\s*=\s*function', rt)) | set(re.findall(r'\b(\w+)\s*=\s*function', rt)) \
    | set(re.findall(r'function\s+[\w.]+[.:](\w+)\s*\(', rt)) | set(re.findall(r'\[\s*"(\w+)"\s*\]\s*=', rt))
calls = collections.defaultdict(set)
fcalls = collections.defaultdict(set)
script_def = set()
for root, _, files in os.walk(LUA):
    for f in files:
        if not f.endswith('.lua'):
            continue
        s = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
        pkg = os.path.relpath(root, LUA).split(os.sep)[0]
        if pkg == '@lib':
            pkg = '@' + os.path.relpath(root, LUA).split(os.sep)[1]
        script_def |= set(re.findall(r'__P__:(?:override|method|func)\(\s*"(?:\w+)"\s*,\s*"(\w+)"', s))
        script_def |= set(re.findall(r'__P__:func\(\s*"(\w+)"', s))
        script_def |= set(re.findall(r'__P__:\w+\(\s*"\w+"\s*,\s*"(\w+)"', s))
        for m in re.findall(r'\bmc\([^,()]+(?:\([^()]*\))?[^,()]*,\s*"(\w+)"', s):
            calls[m].add(pkg)
        for m in re.findall(r'\bF\.(\w+)', s):
            fcalls[m].add(pkg)
miss = [(n, p) for n, p in calls.items() if n not in rt_def and n not in script_def]
fmiss = [(n, p) for n, p in fcalls.items() if n not in rt_def and n not in script_def]
print('== methods called, defined nowhere (%d)' % len(miss))
for n, p in sorted(miss, key=lambda x: -len(x[1])):
    print('%4d  %-28s %s' % (len(p), n, ', '.join(sorted(p)[:4])))
print('== builtins F.x, defined nowhere (%d)' % len(fmiss))
for n, p in sorted(fmiss, key=lambda x: -len(x[1])):
    print('%4d  %-28s %s' % (len(p), n, ', '.join(sorted(p)[:4])))
