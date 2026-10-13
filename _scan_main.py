import os,re,json,collections
GP=r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages'
M1='-- [px2jelly] merged drafts below'
stats=collections.Counter(); odd=[]
rows={}
for pkg in sorted(os.listdir(GP)):
    f=os.path.join(GP,pkg,'0.0.1','main.lua')
    if not os.path.exists(f): continue
    s=open(f,encoding='utf-8',errors='replace').read()
    lines=s.split('\n')
    i1=next((i for i,l in enumerate(lines) if l.startswith(M1)),None)
    i2=next((i for i,l in enumerate(lines) if l.startswith('-- [pxcompat] autowire')),None)
    head='\n'.join(lines[:i1]) if i1 is not None else None
    dr='\n'.join(lines[i1:i2]) if (i1 is not None and i2 is not None) else ''
    rows[pkg]=dict(i1=i1,i2=i2,n=len(lines),
      hw=len(re.findall(r'registerCustomWeapon\(',head or s)), dw=len(re.findall(r'registerCustomWeapon\(',dr)),
      dspr=len(re.findall(r'registerCustomSprite\(',dr)), ds=len(re.findall(r'registerCustom\w+\(',dr)),
      reg=len(re.findall(r'registerCallback_\w+',dr)))
    stats['pk']+=1
    if i1 is None: stats['no_m1']+=1
    if i2 is None: stats['no_m2']+=1
    if rows[pkg]['dw']: stats['draft_has_weapon']+=1; odd.append(pkg)
    if rows[pkg]['reg']: stats['draft_registers_cb']+=1
print(stats)
print('drafts registering weapons:',odd[:40])
json.dump(rows,open(r'C:\Users\Admin\pxrt_dev\out\main_scan.json','w'))
