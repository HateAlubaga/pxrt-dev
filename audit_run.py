"""Mass read-only audit through the router: one claude-cheap worker per job, report -> audit/<job>.md.
usage: py -3.10 audit_run.py [--par N] [job-substring ...]   (skips jobs whose report exists)"""
import os, re, sys, json, subprocess, time, threading
DEV = r'C:\Users\Admin\pxrt_dev'
GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
PK = os.path.join(GAME, 'jelly', 'packages')
OUT = os.path.join(DEV, 'audit')
os.makedirs(OUT, exist_ok=True)

COMMON = r'''You audit part of "pxrt": a runtime that runs ProjectX (PX) scripts for Worms Armageddon 3.8.1, transpiled
from PX C-like sources (.pxc) to Lua 5.3, inside the wkJellyWorm DLL. Goal: exact PX behaviour and low CPU cost.
Locations (read-only; do NOT edit, create or run anything):
- runtime: C:\Users\Admin\pxrt_dev\pxrt_core.lua (deployed as pxrt.lua), pxrt_engine.lua, pxrt_e_*.lua
- transpiled package scripts: C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\<package>\*.lua
- PX sources: "C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\<package>\0.0.1\scripts_px\*.pxc"
- PX shared libraries (utils, wosc_lib, p_sprite_builder ...): C:\Users\Admin\pxrt_dev\px_pipeline\pxl\*.pxc
- known in-game log lines: "method CheckName called on null", "AddInterfaceBitmap unsupported",
  "beam_glow.png not found", "RenderQuad outside a custom render function".
Report format (markdown, your final answer is saved as the report):
## Findings
One bullet per finding: `path:line` - severity (high/med/low) - what is wrong - concrete scenario - suggested fix.
Only real, specific findings you verified by reading the code. No style remarks. At most 15 findings.
If nothing found, write "No findings".
## Notes
Short list of anything you could not check.
'''

RT = ['pxrt_core.lua', 'pxrt_engine.lua', 'pxrt_e_consts.lua', 'pxrt_e_game.lua', 'pxrt_e_funcs.lua', 'pxrt_e_structs.lua',
      'pxrt_e_classes.lua', 'pxrt_e_terrain.lua', 'pxrt_e_pseudo.lua', 'pxrt_e_soft.lua', 'pxrt_e_extra.lua',
      'pxrt_e_quads.lua', 'pxrt_e_hooks.lua']


def jobs():
    js = {}
    for f in RT:
        js['rt_' + f[:-4]] = COMMON + '\nTASK: audit runtime module C:\\Users\\Admin\\pxrt_dev\\%s. Look for: wrong ' \
            'semantics vs ProjectX (fixed-point, integer/float, null objects, return values), nil-index errors, ' \
            'pcall-swallowed failures that silently disable features, stubs that should do something, and per-frame ' \
            'CPU waste (allocations, closures, string ops in hot paths). Read other runtime files only as needed.' % f
    claimed = re.findall(r'^(\S+): claimed', open(os.path.join(GAME, 'jelly', 'pxboot.log'), encoding='latin-1').read(), re.M)
    for p in claimed + ['utility_hangglider']:
        js['pkg_' + p] = COMMON + '\nTASK: audit package %s. Read its .pxc sources and its transpiled Lua, then check ' \
            'every engine call / field / override it uses against the runtime (grep the runtime for the name). ' \
            'Report PX features this package needs that the runtime stubs, ignores, or implements differently, ' \
            'and transpilation mistakes (compare .pxc with the Lua line by line for the important functions). ' \
            'utility_hangglider is NOT run by pxrt: it is a hand-written Lua port in jelly\\packages\\utility_hangglider' \
            '\\0.0.1\\main.lua; for it compare that port with px_pipeline\\testout\\lua\\utility_hangglider\\paratest.lua ' \
            'and the PX source utility_hangglider_render\\0.0.1\\scripts_px\\paratest.pxc (controls, physics).' % p
    js['perf_dispatch'] = COMMON + '\nTASK: CPU cost of message dispatch. In-game profile: pxrt.lua:58 (ti) 7%, ' \
        'pxrt_e_hooks.lua inner vtable8 dispatch 6.7%, pxrt_engine.lua:284 (proxy __index) 6.5%, pxrt.lua:213 (runChain) ' \
        '5.3%, pxrt.lua:506 (globals __index) 3.7%, pxrt.lua:222 (invoke) 3.3%. Read pxrt_core.lua and pxrt_e_hooks.lua ' \
        '(makeVt8) and propose concrete, semantics-preserving optimisations with code sketches (e.g. cached super ' \
        'closures in runChain, avoiding per-message table allocations). Rank by expected gain.'
    js['perf_proxy'] = COMMON + '\nTASK: CPU cost of object field access: pxrt_engine.lua getMT/__index/__newindex ' \
        '(fieldSpec, kinds i/f/p/w), the globals table __index in pxrt_core.lua, and ti/tf conversions. Top script ' \
        'functions in-game: p_sprite_builder WormSprite::Message 11%, helicopter_SCRIPT.lua:122 9%, spitfire_SCRIPT.lua:40 ' \
        '8.5%, utils_red.lua:1998 7%, wosc_lib.lua:74/129 10%. Read those transpiled functions too and say what in the ' \
        'runtime makes them expensive. Propose concrete optimisations with code sketches, ranked by expected gain.'
    return js


# claude-cheap.cmd -> claude.cmd expects claude-code\<ver>\claude.exe, but the app now keeps it one level deeper
# (claude-code\<ver>\<hash>\claude.exe): call the newest exe directly with claude-cheap's environment.
import glob
EXE = max(glob.glob(os.path.join(os.environ['APPDATA'], 'Claude', 'claude-code', '*', '*', 'claude.exe')) +
          glob.glob(os.path.join(os.environ['APPDATA'], 'Claude', 'claude-code', '*', 'claude.exe')), key=os.path.getmtime)
ENV = dict(os.environ)
ENV.update({
    'ANTHROPIC_BASE_URL': os.environ.get('OMNIROUTE_URL', 'http://127.0.0.1:20128'),
    'ANTHROPIC_AUTH_TOKEN': os.environ.get('OMNIROUTE_API_KEY', 'local'), 'ANTHROPIC_API_KEY': '',
    'ANTHROPIC_MODEL': 'cheap', 'ANTHROPIC_DEFAULT_OPUS_MODEL': 'cheap', 'ANTHROPIC_DEFAULT_SONNET_MODEL': 'cheap',
    'ANTHROPIC_DEFAULT_HAIKU_MODEL': 'cheap-fast', 'CLAUDE_CODE_SUBAGENT_MODEL': 'cheap-fast',
    'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'CLAUDE_KIT_WORKER': '1',
    'CLAUDE_CODE_MAX_CONTEXT_TOKENS': '128000',
})
ENV.pop('CLAUDECODE', None)


def run(job, prompt):
    t0 = time.time()
    try:
        r = subprocess.run([EXE, '--setting-sources', 'project,local', '-p', '--output-format', 'json',
                            '--allowedTools', 'Read,Grep,Glob', '--permission-mode', 'default'],
                           input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace',
                           cwd=DEV, timeout=1800, env=ENV)
        out = r.stdout
        try:
            txt = json.loads(out).get('result') or out
        except Exception:
            txt = out + '\n' + r.stderr[-2000:]
    except subprocess.TimeoutExpired:
        txt = 'TIMEOUT'
    with open(os.path.join(OUT, job + '.md'), 'w', encoding='utf-8') as f:
        f.write('# %s\n\n%s\n' % (job, txt))
    print('%s done %.0fs %d chars' % (job, time.time() - t0, len(txt)), flush=True)


def main():
    args = sys.argv[1:]
    par = 4
    if args[:1] == ['--par']:
        par = int(args[1]); args = args[2:]
    js = jobs()
    todo = [(k, v) for k, v in js.items() if (not args or any(a in k for a in args))
            and not os.path.exists(os.path.join(OUT, k + '.md'))]
    print('%d jobs' % len(todo), flush=True)
    lock = threading.Lock()

    def worker():
        while True:
            with lock:
                if not todo:
                    return
                k, v = todo.pop(0)
            run(k, v)
    ts = [threading.Thread(target=worker) for _ in range(par)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    idx = ['# Audit index\n']
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.md') and f != 'INDEX.md':
            s = open(os.path.join(OUT, f), encoding='utf-8').read()
            n = len(re.findall(r'^\s*[-*] `?[\w\\/.:-]+:\d+', s, re.M))
            idx.append('- %s: %d findings' % (f[:-3], n))
    open(os.path.join(OUT, 'INDEX.md'), 'w', encoding='utf-8').write('\n'.join(idx) + '\n')
    print('finished', flush=True)


main()
