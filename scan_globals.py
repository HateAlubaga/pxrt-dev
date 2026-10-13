import os, re, collections, sys
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *
c = collections.Counter()
ex = {}
for root, ds, fs in os.walk(LUA):
    for f in fs:
        if f.endswith('.lua'):
            s = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
            s2 = re.sub(r'"(?:[^"\\]|\\.)*"', '""', s)
            for m in re.findall(r'(?<![\w.:])(math|string|table|os|io|pairs|ipairs|tostring|tonumber|type|select|next|print|error|assert|pcall|rawget|rawset|setmetatable|getmetatable|unpack|require)\b(?=[.(])', s2):
                c[m] += 1
                ex.setdefault(m, os.path.join(root, f))
print(c.most_common())
for k, v in ex.items():
    print(k, v)
