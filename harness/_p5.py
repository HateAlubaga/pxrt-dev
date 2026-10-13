p = r'C:\Users\Admin\pxrt_dev\harness\bench.py'
s = open(p, encoding='utf-8').read()
old = "    out = harness.sync_runtime()\n"
new = "    out = pxgen.OUT_LIBS if os.environ.get('BENCH_NOSYNC') else harness.sync_runtime()\n"
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
