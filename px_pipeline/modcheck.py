"""Static sanity check of every jelly package (primitive errors only).

The DLL loads manifest.json, checks scripts/sprites/imgs exist, then runs only
scripts[0] in a per-package environment that falls back to globals.
require() resolves only jelly/lualibs/*.lua (case-insensitive).

Checks (latest version dir of each package):
  MANIFEST   bad JSON / missing required field / listed file missing (package refused).
  SYNTAX     tokenizer + block/bracket balance on scripts[0] (missing end, stray char...).
  BADOP      C-isms Lua rejects: != += -= && || !x
  REQUIRE    require of a name that is not a lualib (DLL returns an error string).
  UNDEF      call to a global function nobody defines (script, lualibs, DLL, stdlib).
  STRUCTFLD  WeaponStruct.unknownXX the DLL does not bind.
  SPRITE     projectile sprite slot (0x60/0x124/0x170) set only to a literal >= 1024.
  ASSET      string literal naming a .png/.img/.wav/.spr/.bmp that exists nowhere.
  FMT_D      string.format "%d" with a division in its arguments (5.4 errors on fractions).
  DUPNAME    same weapon name registered by two active packages.
"""
import os, re, sys, glob, json, configparser, collections

GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
JELLY = os.path.join(GAME, 'jelly')
PKGS = os.path.join(JELLY, 'packages')
HERE = os.path.dirname(os.path.abspath(__file__))

KEYWORDS = set('''and break do else elseif end false for function goto if in local nil not or
repeat return then true until while'''.split())
STDLIB = set('''print pairs ipairs type tostring tonumber pcall xpcall error assert select next
rawget rawset rawequal rawlen setmetatable getmetatable require load loadstring dofile loadfile
unpack collectgarbage string table math os io coroutine debug utf8 bit32 _G _ENV module
setfenv getfenv newproxy gcinfo self arg warn'''.split())
REQUIRED = ["name", "description", "version", "author", "scripts", "sprites", "imgs", "dependencies"]

TOKEN_RE = re.compile(r'''
  (?P<ws>[ \t\r\f\v]+|\n)
 |(?P<lcomment>--\[(?P<ceq>=*)\[)
 |(?P<comment>--[^\n]*)
 |(?P<lstr>\[(?P<seq>=*)\[)
 |(?P<str>"(?:[^"\\\n]|\\z\s*|\\(?:.|\n))*"|'(?:[^'\\\n]|\\z\s*|\\(?:.|\n))*')
 |(?P<num>0[xX](?:[0-9a-fA-F]*\.?[0-9a-fA-F]*)(?:[pP][+-]?\d+)?|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
 |(?P<name>[A-Za-z_]\w*)
 |(?P<op>\.\.\.|\.\.|==|~=|<=|>=|//|::|<<|>>|[-+*/%^\#&~|<>=(){}\[\];:,.])
 |(?P<bad>!=|\+=|-=|\*=|/=|&&|\|\||!|.)
''', re.X | re.S)

def tokenize(text):
    """Return (tokens, errors). Token = (kind, value, line)."""
    toks, errs = [], []
    pos, line, n = 0, 1, len(text)
    if text.startswith('#'):  # shebang
        pos = text.find('\n') if '\n' in text else n
    while pos < n:
        m = TOKEN_RE.match(text, pos)
        kind = m.lastgroup
        if kind in ('ceq', 'seq'):
            kind = 'lcomment' if m.group('lcomment') else 'lstr'
        val = m.group(0)
        if kind in ('lcomment', 'lstr'):
            eq = m.group('ceq') if kind == 'lcomment' else m.group('seq')
            close = ']' + eq + ']'
            end = text.find(close, m.end())
            if end < 0:
                errs.append(('SYNTAX', line, 'unfinished long %s' % ('comment' if kind == 'lcomment' else 'string')))
                return toks, errs
            val = text[pos:end + len(close)]
            if kind == 'lstr':
                toks.append(('str', val, line))
            line += val.count('\n')
            pos = end + len(close)
            continue
        if kind == 'bad':
            if val in ('"', "'"):
                errs.append(('SYNTAX', line, 'unfinished string'))
                nl = text.find('\n', pos)
                pos = n if nl < 0 else nl
                continue
            if val in ('!=', '+=', '-=', '*=', '/=', '&&', '||', '!'):
                errs.append(('BADOP', line, "'%s' is not Lua" % val))
            else:
                errs.append(('SYNTAX', line, 'unexpected symbol %r' % val))
        elif kind == 'name':
            toks.append(('kw' if val in KEYWORDS else 'name', val, line))
        elif kind in ('str', 'num', 'op'):
            toks.append((kind, val, line))
        line += val.count('\n')
        pos = m.end()
    return toks, errs

BLOCK_OPEN = {'function', 'if', 'do', 'while', 'for', 'repeat'}
PAIR = {')': '(', ']': '[', '}': '{'}

def balance(toks):
    errs, stack = [], []   # entries: [what, line]
    for i, (k, v, ln) in enumerate(toks):
        if k == 'kw':
            if v in ('function', 'if', 'repeat', 'while', 'for'):
                stack.append([v, ln])
            elif v == 'do':
                if stack and stack[-1][0] in ('while', 'for'):
                    stack[-1][0] = 'loop'
                else:
                    stack.append(['do', ln])
            elif v in ('then',):
                if not stack or stack[-1][0] != 'if':
                    errs.append(('SYNTAX', ln, "'then' without 'if'"))
                    return errs
            elif v in ('elseif', 'else'):
                if not stack or stack[-1][0] != 'if':
                    errs.append(('SYNTAX', ln, "'%s' without 'if'" % v))
                    return errs
            elif v == 'end':
                if not stack or stack[-1][0] not in ('function', 'if', 'do', 'loop'):
                    top = stack[-1] if stack else None
                    errs.append(('SYNTAX', ln, "'end' closes %s" % (
                        "nothing (extra 'end')" if not top else "'%s' opened at line %d" % tuple(top))))
                    return errs
                stack.pop()
            elif v == 'until':
                if not stack or stack[-1][0] != 'repeat':
                    errs.append(('SYNTAX', ln, "'until' without 'repeat'"))
                    return errs
                stack.pop()
        elif k == 'op':
            if v in '([{':
                stack.append([v, ln])
            elif v in ')]}':
                if not stack or stack[-1][0] != PAIR[v]:
                    top = stack[-1] if stack else None
                    errs.append(('SYNTAX', ln, "'%s' closes %s" % (v,
                        'nothing' if not top else "'%s' opened at line %d" % tuple(top))))
                    return errs
                stack.pop()
    if stack:
        what, ln = stack[-1]
        errs.append(('SYNTAX', ln, "'%s' opened here is never closed (missing %s)" % (
            what, {'(': "')'", '[': "']'", '{': "'}'", 'repeat': "'until'"}.get(what, "'end'"))))
    return errs

def names_bound_called(toks):
    bound, called = set(), []
    for i, (k, v, ln) in enumerate(toks):
        if k != 'name':
            continue
        prev = toks[i - 1] if i else ('', '', 0)
        nxt = toks[i + 1] if i + 1 < len(toks) else ('', '', 0)
        after_dot = prev[0] == 'op' and prev[1] in ('.', ':')
        if after_dot or (prev[0] == 'op' and prev[1] == '::'):
            continue
        # definitions
        if prev[1] in ('local', 'function', 'for', 'goto') or (prev[0] == 'op' and prev[1] == ',') \
                or (nxt[0] == 'op' and nxt[1] in ('=', ',')):
            bound.add(v)
        if prev[0] == 'op' and prev[1] == '(' and i >= 2 and toks[i - 2][1] == 'function':
            bound.add(v)
        if prev[0] == 'op' and prev[1] == '(' and i >= 3 and toks[i - 3][1] == 'function':
            bound.add(v)
        # function f(a, b): params after '(' following function name chain
        # calls
        if nxt[0] == 'str' or (nxt[0] == 'op' and nxt[1] in ('(', '{')):
            if prev[1] != 'function':
                called.append((v, ln))
    # parameters: scan "function ... ( names )"
    for i, (k, v, ln) in enumerate(toks):
        if v == 'function' and k == 'kw':
            j = i + 1
            while j < len(toks) and toks[j][1] != '(':
                j += 1
            j += 1
            while j < len(toks) and toks[j][1] != ')':
                if toks[j][0] == 'name':
                    bound.add(toks[j][1])
                j += 1
    return bound, called

def read(p):
    return open(p, encoding='utf-8', errors='replace').read()

def dll_globals():
    return set(l.strip() for l in open(os.path.join(HERE, 'dll_globals.txt')) if l.strip())

def lualib_info():
    names, libs = set(), set()
    for p in glob.glob(os.path.join(JELLY, 'lualibs', '*.lua')):
        libs.add(os.path.splitext(os.path.basename(p))[0].lower())
        toks, _ = tokenize(read(p))
        b, _ = names_bound_called(toks)
        names |= b
        names.add(os.path.splitext(os.path.basename(p))[0])
    return names, libs

def weaponstruct_fields():
    p = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\CustomWeapons.cpp'
    t = read(p) + read(p.replace('.cpp', '.h'))
    return set(re.findall(r'"(unknown[0-9A-Fa-f]+)"', t))

def active_packages():
    cp = configparser.ConfigParser(strict=False, interpolation=None, allow_no_value=True)
    cp.optionxform = str
    cp.read_string(read(os.path.join(GAME, 'wkJellyWorm.ini')))
    act = set()
    if cp.has_section('autostart'):
        for k, v in cp.items('autostart'):
            v = (v or '').split(';')[0].strip()
            if v and v != '0':
                act.add(k)
    return act

def latest_dir(pkg):
    vers = [d for d in glob.glob(os.path.join(PKGS, pkg, '*')) if os.path.isdir(d)]
    if not vers:
        return None
    def key(d):
        return [int(x) if x.isdigit() else 0 for x in re.split(r'[.\-]', os.path.basename(d))]
    return max(vers, key=key)

FILE_RE = re.compile(r'["\']([^"\'\n]{1,200}\.(?:png|img|wav|spr|bmp))["\']', re.I)

def asset_exists(pkgdir, ref):
    ref_n = ref.replace('\\', '/').lstrip('/')
    base = os.path.basename(ref_n)
    cands = [os.path.join(pkgdir, ref_n), os.path.join(pkgdir, 'assets', ref_n),
             os.path.join(pkgdir, 'assets', base), os.path.join(pkgdir, base),
             os.path.join(GAME, ref_n), os.path.join(JELLY, ref_n),
             os.path.join(JELLY, 'sprites', base), os.path.join(JELLY, 'sounds', base),
             os.path.join(JELLY, 'placeholders', base),
             os.path.join(GAME, 'DATA', ref_n), os.path.join(GAME, 'User', ref_n)]
    return any(os.path.exists(c) for c in cands)

def check_package(pkgdir, known, libs, fields):
    issues = []
    mpath = os.path.join(pkgdir, 'manifest.json')
    if not os.path.exists(mpath):
        return [('MANIFEST', 'no manifest.json')], []
    try:
        man = json.loads(read(mpath))
    except Exception as e:
        return [('MANIFEST', 'bad JSON: %s' % str(e)[:120])], []
    miss = [f for f in REQUIRED if f not in man]
    if miss:
        issues.append(('MANIFEST', 'missing fields: %s (package refused)' % ' '.join(miss)))
    for f in ('scripts', 'sprites', 'imgs'):
        for fn in man.get(f) or []:
            if not os.path.exists(os.path.join(pkgdir, fn)):
                issues.append(('MANIFEST', 'listed %s file missing: %s (package refused)' % (f, fn)))
    scripts = man.get('scripts') or []
    if not scripts:
        issues.append(('MANIFEST', 'no scripts'))
        return issues, []
    main = os.path.join(pkgdir, scripts[0])
    if not os.path.exists(main):
        return issues, []
    t = read(main)
    rel = scripts[0]
    toks, errs = tokenize(t)
    errs += balance(toks)
    for kind, ln, msg in errs:
        issues.append((kind, '%s:%d %s' % (rel, ln, msg)))
    for i, (k, v, ln) in enumerate(toks):
        if v == 'require' and k == 'name' and i + 1 < len(toks):
            nx = toks[i + 1]
            if nx[1] == '(' and i + 2 < len(toks):
                nx = toks[i + 2]
            if nx[0] == 'str':
                lib = nx[1].strip('"\'')
                if lib.lower() not in libs:
                    issues.append(('REQUIRE', '%s:%d require("%s") is not a lualib' % (rel, ln, lib)))
    bound, called = names_bound_called(toks)
    seen = set()
    for name, ln in called:
        if name in bound or name in known or name in seen:
            continue
        seen.add(name)
        issues.append(('UNDEF', '%s:%d calls %s() which nothing defines' % (rel, ln, name)))
    structs = set(re.findall(r'\b([A-Za-z_]\w*)\s*=\s*(?:WeaponStruct\.new|WeaponStruct\s*\(|cloneVanillaWeapon)\s*\(?', t))
    for s in structs:
        for fld in sorted(set(re.findall(r'(?<![\w.])' + re.escape(s) + r'\.(unknown[0-9A-Fa-f]+)\s*=', t))):
            if fields and fld not in fields:
                issues.append(('STRUCTFLD', '%s: %s.%s is not a WeaponStruct field' % (rel, s, fld)))
        for slot in ('unknown60', 'unknown124', 'unknown170'):
            vals = re.findall(r'(?<![\w.])' + re.escape(s) + r'\.' + slot + r'\s*=\s*([^\r\n;]+?)\s*(?:--.*)?$', t, re.M)
            lits = [v for v in vals if re.fullmatch(r'-?\d+', v)]
            if vals and len(lits) == len(vals) and int(lits[-1]) >= 1024:
                issues.append(('SPRITE', '%s: %s.%s = %s (no sprite, projectile invisible)' % (rel, s, slot, lits[-1])))
    for ref in sorted(set(FILE_RE.findall(t))):
        if any(ch in ref for ch in '%$*') or '..' in ref:
            continue
        if not asset_exists(pkgdir, ref):
            issues.append(('ASSET', '%s: missing file "%s"' % (rel, ref)))
    for m in re.finditer(r'string\.format\s*\(\s*(["\'])(.*?)\1\s*,([^\n]*)', t):
        fmt, args = m.group(2), m.group(3)
        if re.search(r'%[-+ #0]*\d*d', fmt) and re.search(r'[^/]/[^/]', args) and 'floor' not in args:
            issues.append(('FMT_D', '%s:%d %%d with division: %s' % (rel, t.count('\n', 0, m.start()) + 1, args.strip()[:80])))
    names = []
    for m in re.finditer(r'registerCustomWeapon\s*\(([^)]*)\)', t, re.S):
        strs = re.findall(r'"([^"]*)"', m.group(1))
        if strs:
            names.append(strs[0])
    for m in re.finditer(r'\.name1\s*=\s*"([^"]+)"', t):
        names.append(m.group(1))
    return issues, names

def main():
    lnames, libs = lualib_info()
    known = STDLIB | dll_globals() | lnames
    fields = weaponstruct_fields()
    act = active_packages()
    only_active = '--active' in sys.argv
    pkgs = sorted(d for d in os.listdir(PKGS) if os.path.isdir(os.path.join(PKGS, d)))
    order = [p for p in pkgs if p in act] + ([] if only_active else [p for p in pkgs if p not in act])
    counts, act_counts = collections.Counter(), collections.Counter()
    bad_pkgs = collections.Counter()
    weapon_names = collections.defaultdict(set)
    out = []
    for pkg in order:
        d = latest_dir(pkg)
        if not d:
            continue
        issues, names = check_package(d, known, libs, fields)
        if pkg in act:
            for n in names:
                weapon_names[n].add(pkg)
        for kind, _ in issues:
            counts[kind] += 1
            if pkg in act:
                act_counts[kind] += 1
        for kind in set(k for k, _ in issues):
            bad_pkgs[kind] += 1
        if issues:
            out.append('== %s%s (%s)' % (pkg, ' [ACTIVE]' if pkg in act else '', os.path.basename(d)))
            for kind, msg in issues:
                out.append('  %-9s %s' % (kind, msg))
    dup = ['  DUPNAME   "%s" in %s' % (n, ', '.join(sorted(ps))) for n, ps in sorted(weapon_names.items()) if len(ps) > 1]
    print('packages: %d, active: %d, WeaponStruct fields known: %d' % (len(pkgs), len(act & set(pkgs)), len(fields)))
    print('issues total:', dict(counts))
    print('issues in active:', dict(act_counts))
    print('packages with issue kind:', dict(bad_pkgs))
    print('\n'.join(dup))
    print('\n'.join(out))

if __name__ == '__main__':
    main()
