import os,re,collections
root=r'C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua'
files={}
for dp,_,fs in os.walk(root):
    for f in fs:
        if f.endswith('.lua'):
            p=os.path.join(dp,f); files[p]=open(p,encoding='utf-8',errors='replace').read()
GV=collections.defaultdict(set)
for p,s in files.items():
    for m in re.finditer(r'__P__:gvars\(\{([^}]*)\}\)',s):
        for n in re.findall(r'"(\w+)"',m.group(1)): GV[n].add(p)
res=collections.defaultdict(list)
for p,s in files.items():
    pk=p[len(root)+1:].split(os.sep)[0]
    for m in set(re.findall(r'\bself\.(\w+)',s)):
        if m in GV and p not in GV[m]:
            if re.search(r'\.'+m+r'\s*=[^=]',s): continue
            res[pk].append(m)
for k,v in sorted(res.items()): print(k,sorted(set(v)))
print(len(res))
