import json, re
c = json.load(open(r'C:\Users\Admin\pxrt_dev\px_pipeline\corpus.json', encoding='utf-8'))
unp = []   # a & b == c   or a | b == c  (no parens)
par = []   # (a & b) == c
for k, s in c.items():
    for i, line in enumerate(s.split('\n')):
        l = line.split('//')[0]
        if re.search(r'[\w\)\]]\s*&\s*[\w\(]+\s*(==|!=)', l) and '&&' not in l.replace('&&', '') :
            unp.append((k, i + 1, l.strip()))
        if re.search(r'\([^()]*[^&]&[^&][^()]*\)\s*(==|!=)', l):
            par.append((k, i + 1, l.strip()))
print('unparenthesised & ==:', len(unp), ' parenthesised:', len(par))
for x in unp[:25]:
    print(x)
print('---')
for x in par[:8]:
    print(x)
