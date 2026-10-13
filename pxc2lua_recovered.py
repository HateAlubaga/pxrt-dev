"""PX script (.pxc) -> Lua 5.3 transpiler.

Every .pxc file becomes one Lua chunk.  A chunk is loaded by pxrt.lua as
    load(src, "@pkg/file.pxc", "t", {})(__R__, __P__, __G__)
where __R__ is the runtime, __P__ the package object (registration API) and
__G__ the package global table (chained to libs, then engine).

usage:
  py -3.10 pxc2lua.py FILE.pxc [...]          compile single files (own package decls)
  py -3.10 pxc2lua.py --pkg NAME [...]        compile packages into OUTDIR/<pkg>/
  py -3.10 pxc2lua.py --all                   compile everything, write report
  options: --out DIR (default testout/lua)  --check (compile output with lupa)
"""
import json, os, re, sys, collections
from pxast import parse, PXError
from pxsym import corpus, parsed, packages, package_decls, script_classes, lib_files, ENTRY_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
CLASSES = json.load(open(os.path.join(HERE, "px", "classes.json"), encoding="utf-8"))
CENSUS = json.load(open(os.path.join(HERE, "px", "census.json"), encoding="utf-8"))

LUA_KW = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if",
          "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"}
RESERVED = {"T", "ti", "tf", "div", "mod", "isnull", "K", "F", "call", "mc", "self", "super",
            "__R__", "__P__", "__G__", "_ENV", "_"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
ALLCAPS = re.compile(r"[A-Z][A-Z0-9_]*\Z")
ENGINE_GLOBALS = {"GS", "GG", "Root", "Env"}
CONST_PREFIXES = ("M_", "WS_", "OC_", "CT_", "DT_", "WCT_", "CM_", "LAYER_", "CMASK_", "TI_",
                  "EObjectClass")
BASIC = {"int", "fixed", "float", "bool", "string", "void"}

ENGINE_INHERIT = {"CWorm": "CGObject", "CMissile": "CGObject", "CMine": "CGObject",
                  "CCrate": "CGObject", "COilDrum": "CGObject", "CGas": "CGObject",
                  "CArrow": "CGObject", "CCanister": "CGObject", "CCross": "CGObject",
                  "CGObject": "CObject", "CTurnGame": "CObject", "CTeam": "CObject",
                  "CFilter": "CObject", "CLand": "CObject", "CGameState": "CObject"}

# engine method names per class (from wiki dump)
ENGINE_METHODS = {}
for _c, _v in CLASSES.items():
    ms = set()
    for sig in _v.get("methods", []):
        if sig.startswith("[constructor]"):
            continue
        m = re.search(r"(\w+)\s*\(", sig)
        if m:
            ms.add(m.group(1))
    ENGINE_METHODS[_c] = ms
ALL_ENGINE_METHODS = set().union(*ENGINE_METHODS.values())


def type_kind(base, ptr=0, ndims=0):
    if ndims or ptr:
        return "obj"
    if base in ("int", "bool") or re.match(r"E[A-Z]", base):
        return "int"
    if base in ("fixed", "float"):
        return "float"
    if base == "string":
        return "str"
    if base == "void":
        return "any"
    return "obj"


FIELD_KINDS = {}
for _c, _v in CLASSES.items():
    for fname, ftype in _v.get("fields", []):
        m = re.match(r"(\w+)\s*(\*?)", ftype or "")
        if not m or " " in (ftype or "").strip() and not ftype.strip().endswith("*") and "[" not in ftype:
            continue
        FIELD_KINDS[fname] = type_kind(m.group(1), 1 if (m.group(2) or "[" in ftype) else 0)
FIELD_KINDS.update({"TurnSide": "int", "WormTeam": "int", "WormNumber": "int", "WeaponN": "int",
                    "JetFuel": "int", "CanFire": "int", "SelectX": "int", "SelectY": "int",
                    "FirePower": "any", "FireAngle": "any", "CurWeapon": "obj", "Water": "any",
                    "Gravity": "any", "Wind": "any", "Tick": "int", "ObjState": "int"})

# free builtins seen in the corpus (callable without object); names that are also engine
# methods are resolved at runtime in method context (`call`).
FREE_BUILTINS = set(n for n, _ in CENSUS["call_free"]) | set(CENSUS["arity"].keys())
RET_KIND = {"sqrt": "float", "sin": "float", "cos": "float", "atan2": "float", "atan": "float",
            "tan": "float", "asin": "float", "acos": "float", "float": "float", "fixed": "float",
            "int": "int", "StrLen": "int", "atoi": "int", "random": "int", "GetLocalMachine": "int",
            "IsReplay": "int", "IsMultiplayer": "int", "StrCmp": "int", "RGB": "int", "ARGB": "int",
            "StrCon": "str", "ItoA": "str", "StrLeft": "str", "StrRight": "str", "ftoa": "str",
            "MakeNumberString": "str", "LoadSprite": "obj", "GetWeaponByName": "obj",
            "GetCurrentWorm": "obj", "LoadImage": "obj", "MakeBitmap": "obj"}


class CompileError(Exception):
    pass


def lstr(s):
    try:
        b = s.encode("latin-1")
    except UnicodeEncodeError:
        b = s.encode("cp1252", errors="replace")
    out = []
    for ch in b:
        if 32 <= ch < 127 and ch not in (34, 92):
            out.append(chr(ch))
        else:
            out.append("\\%03d" % ch)
    return '"' + "".join(out) + '"'


def flit(v):
    r = repr(float(v))
    if r in ("inf", "-inf", "nan"):
        return "(1/0)" if r == "inf" else ("(-1/0)" if r == "-inf" else "(0/0)")
    if "." not in r and "e" not in r:
        r += ".0"
    return r


def fa(base, name):
    """field access code"""
    if IDENT.match(name) and name not in LUA_KW:
        return "%s.%s" % (base, name)
    return "%s[%s]" % (base, lstr(name))


def ln(n):
    """PX local name -> Lua local name"""
    s = n
    if not IDENT.match(s):
        s = re.sub(r"[^A-Za-z0-9_]", lambda m: "_%x" % ord(m.group()), s)
        if s[0].isdigit():
            s = "_" + s
    if s in LUA_KW or s in RESERVED:
        s += "_"
    return s


def pfx(code):
    """make code usable as a prefix expression (call target / index base)"""
    if (code[:1].isdigit() or code[:1] in ('"', "-", "{") or code.startswith("not ")
            or code in ("nil", "true", "false") or code.startswith("function")):
        return "(%s)" % code
    return code


def const_eval(e, consts):
    k = e[0]
    if k == "num":
        return e[1]
    if k == "bool":
        return 1 if e[1] else 0
    if k == "name":
        return consts.get(e[1])
    if k == "un":
        v = const_eval(e[2], consts)
        if v is None:
            return None
        if e[1] == "-":
            return -v
        if e[1] == "+":
            return v
        if e[1] == "~" and isinstance(v, int):
            return ~v
        return None
    if k == "bin":
        a = const_eval(e[2], consts)
        b = const_eval(e[3], consts)
        if a is None or b is None:
            return None
        op = e[1]
        try:
            if op == "+": return a + b
            if op == "-": return a - b
            if op == "*": return a * b
            if isinstance(a, int) and isinstance(b, int):
                if op == "<<": return a << b
                if op == ">>": return a >> b
                if op == "|": return a | b
                if op == "&": return a & b
                if op == "/" and b: return int(a / b)
        except Exception:
            return None
    return None


# ---------------------------------------------------------------- AST walkers
def walk_stmt(s, fs, fe):
    """visit statements (fs) and top expressions (fe)"""
    if s is None:
        return
    fs(s)
    k = s[0]
    if k == "block":
        for x in s[1]:
            walk_stmt(x, fs, fe)
    elif k == "if":
        fe(s[1]); walk_stmt(s[2], fs, fe); walk_stmt(s[3], fs, fe)
    elif k == "while":
        fe(s[1]); walk_stmt(s[2], fs, fe)
    elif k == "for":
        walk_stmt(s[1], fs, fe)
        if s[2] is not None: fe(s[2])
        if s[3] is not None: fe(s[3])
        walk_stmt(s[4], fs, fe)
    elif k == "ret":
        if s[1] is not None: fe(s[1])
    elif k == "decl":
        for (n, dims, init, extra) in s[2]:
            for d in dims: fe(d)
            if init is not None: fe(init)
    elif k == "local":
        for (n, init) in s[1]:
            if init is not None: fe(init)
    elif k in ("expr",):
        fe(s[1])
    elif k == "delete":
        fe(s[1])


def walk_expr(e, f):
    if e is None or not isinstance(e, tuple):
        return
    f(e)
    k = e[0]
    if k == "call":
        walk_expr(e[1], f)
        for a in e[2]: walk_expr(a, f)
    elif k in ("idx",):
        walk_expr(e[1], f); walk_expr(e[2], f)
    elif k == "mem":
        walk_expr(e[1], f)
    elif k == "un":
        walk_expr(e[2], f)
    elif k == "bin":
        walk_expr(e[2], f); walk_expr(e[3], f)
    elif k == "asg":
        walk_expr(e[2], f); walk_expr(e[3], f)
    elif k in ("post", "pre"):
        walk_expr(e[2], f)
    elif k == "new":
        for a in (e[2] or []): walk_expr(a, f)
        if e[3] is not None: walk_expr(e[3], f)
    elif k == "is":
        walk_expr(e[1], f)


def func_locals(f):
    names = set(p[1] for p in f["params"] if p[1])

    def fs(s):
        if s[0] == "decl":
            for d in s[2]:
                names.add(d[0])
        elif s[0] == "local":
            for d in s[1]:
                names.add(d[0])
    walk_stmt(f["body"], fs, lambda e: None)
    return names


# ---------------------------------------------------------------- compile unit
class Unit:
    """symbols visible while compiling a set of files (package or lib)"""

    def __init__(self, decls, all_files):
        self.d = decls
        self.script_free = set(decls.funcs) | {n for (c, n) in decls.entries if n not in ENTRY_NAMES}
        self.script_classes = {c for (c, n) in decls.entries}
        # enum constants
        self.consts = {}
        self.enum_nonconst = {}
        for k in all_files:
            for node in parsed(k):
                if node[0] == "enum":
                    v = -1
                    for m, e in node[2]:
                        if e is None:
                            v = None if v is None else v + 1
                        else:
                            v = const_eval(e, self.consts)
                        if v is None:
                            self.enum_nonconst[m] = e
                        else:
                            self.consts[m] = v
        # assignment contexts for untyped names
        self.free_asg, self.meth_asg = set(), set()
        for k in all_files:
            ast = parsed(k)
            scls = script_classes(ast, os.path.splitext(os.path.basename(k))[0])
            for node in ast:
                if node[0] != "func" or node[1]["body"] is None:
                    continue
                f = node[1]
                has_self = f["cls"] is not None and not (f["cls"] in scls and not f["override"]
                                                         and f["cls"] != f["name"])
                locs = func_locals(f)
                tgt = self.meth_asg if has_self else self.free_asg

                def fe(e, tgt=tgt, locs=locs):
                    def g(x):
                        if x[0] == "asg" and x[2][0] == "name" and x[2][1] not in locs:
                            tgt.add(x[2][1])
                        elif x[0] in ("post", "pre") and x[2][0] == "name" and x[2][1] not in locs:
                            tgt.add(x[2][1])
                    walk_expr(e, g)
                walk_stmt(f["body"], lambda s: None, fe)
        self.assigned = self.free_asg | self.meth_asg | set(decls.gvars)
        # stats
        self.unres_calls = collections.Counter()
        self.unres_names = collections.Counter()

    def chain(self, cls):
        out = []
        c = cls
        while c and c not in out:
            out.append(c)
            c = self.d.classes.get(c) or ENGINE_INHERIT.get(c)
        return out

    def script_method(self, cls, name):
        return any((c, name) in self.d.methods for c in self.chain(cls))

    def engine_method(self, cls, name):
        return any(name in ENGINE_METHODS.get(c, ()) for c in self.chain(cls))

    def is_class(self, n):
        return (n in self.d.classes or n in CLASSES or n in ENGINE_INHERIT or n in self.d.ctors
                or (re.match(r"C[A-Z]\w*\Z", n) is not None and n not in self.script_free))

    def is_enum_type(self, n):
        return n in self.d.enums or re.match(r"E[A-Z]\w*\Z", n) is not None


# ---------------------------------------------------------------- function codegen
class Fn:
    def __init__(self, unit, f, has_self, has_super, cls):
        self.u = unit
        self.f = f
        self.has_self = has_self
        self.has_super = has_super
        self.cls = cls
        self.scopes = [{}]
        self.loops = []
        self.nlab = 0
        self.ntmp = 0
        self.lines = []
        self.ind = 1
        self.pnames = []

    # ---- scopes
    def push(self):
        self.scopes.append({})

    def pop(self):
        self.scopes.pop()

    def declare(self, n, kind, tkind):
        lname = ln(n)
        self.scopes[-1][n] = (lname, kind, tkind)
        return lname

    def lookup(self, n):
        for sc in reversed(self.scopes):
            if n in sc:
                return sc[n]
        return None

    def tmp(self, p="t"):
        self.ntmp += 1
        return "__%s%d" % (p, self.ntmp)

    def emit(self, s):
        self.lines.append("  " * self.ind + s)

    # ---- value helpers
    def val(self, e):
        c, k = self.ex(e)
        if k == "cond":
            return "(%s and 1 or 0)" % c, "int"
        return c, k

    def cond(self, e):
        c, k = self.ex(e)
        if k == "cond":
            return c
        if k in ("int", "float"):
            return "(%s ~= 0)" % c
        if k == "obj":
            return "(not isnull(%s))" % c
        return "T(%s)" % c

    def conv(self, code, kind, tkind):
        if kind == "cond":
            if tkind == "float":
                return "(%s and 1.0 or 0.0)" % code
            return "(%s and 1 or 0)" % code
        if tkind == "int" and kind != "int":
            return "ti(%s)" % code
        if tkind == "float" and kind != "float":
            return "tf(%s)" % code
        return code

    def args(self, al):
        return ", ".join(self.val(a)[0] for a in al)

    def super_code(self, al=None):
        if not self.has_super:
            return "0"
        if al is None:
            return "super(%s)" % ", ".join(self.pnames)
        return "super(%s)" % self.args(al)

    # ---- names
    def gref(self, n):
        return fa("__G__", n)

    def name_ref(self, n):
        loc = self.lookup(n)
        if loc:
            return loc[0], loc[1]
        u = self.u
        if n in u.consts:
            v = u.consts[n]
            return (str(v) if isinstance(v, int) else flit(v)), ("int" if isinstance(v, int) else "float")
        if n in u.d.gvars:
            g = u.d.gvars[n]
            return self.gref(n), type_kind(g[0], g[1], g[2])
        if n in u.enum_nonconst:
            return self.gref(n), "int"
        if n in ENGINE_GLOBALS:
            return fa("K", n), "obj"
        if n.startswith(CONST_PREFIXES):
            return fa("K", n), "int"
        if ALLCAPS.match(n) and n not in u.assigned:
            u.unres_names["K." + n] += 1
            return fa("K", n), "any"
        if n in u.script_free:
            return self.gref(n), "any"
        if self.has_self:
            if n in u.free_asg and n not in u.meth_asg:
                return self.gref(n), "any"
            return fa("self", n), FIELD_KINDS.get(n, "any")
        if n not in u.assigned:
            u.unres_names[n] += 1
        return self.gref(n), "any"

    def name_tkind(self, n):
        loc = self.lookup(n)
        if loc:
            return loc[2]
        g = self.u.d.gvars.get(n)
        if g:
            k = type_kind(g[0], g[1], g[2])
            return k if k in ("int", "float") else None
        return None

    # ---- lvalues: returns (pre_stmts, target, tkind, rkind)
    def lval(self, e, cache):
        k = e[0]
        if k == "name":
            c, rk = self.name_ref(e[1])
            if c.startswith("K.") or c[:1].isdigit():
                # assignment to engine constant / enum const: keep as global
                c = self.gref(e[1])
            return [], c, self.name_tkind(e[1]), rk
        if k == "mem":
            o, ok = self.ex(e[1])
            pre = []
            if cache and not re.match(r"[A-Za-z_]\w*\Z", o):
                t = self.tmp("o")
                pre.append("local %s = %s" % (t, o))
                o = t
            return pre, fa(pfx(o), e[2]), None, FIELD_KINDS.get(e[2], "any")
        if k == "idx":
            o, ok = self.ex(e[1])
            i, ik = self.val(e[2])
            if ik != "int":
                i = "ti(%s)" % i
            pre = []
            if cache:
                if not re.match(r"[A-Za-z_]\w*\Z", o):
                    t = self.tmp("o")
                    pre.append("local %s = %s" % (t, o))
                    o = t
                if not re.match(r"([A-Za-z_]\w*|-?\d+)\Z", i):
                    t = self.tmp("k")
                    pre.append("local %s = %s" % (t, i))
                    i = t
            return pre, "%s[%s]" % (pfx(o), i), None, "any"
        if k == "un" and e[1] == "*":
            o, ok = self.ex(e[2])
            pre = []
            if cache and not re.match(r"[A-Za-z_]\w*\Z", o):
                t = self.tmp("o")
                pre.append("local %s = %s" % (t, o))
                o = t
            return pre, "%s.v" % pfx(o), None, "any"
        if k == "this":
            return [], "self", None, "obj"
        raise CompileError("bad lvalue %r" % (k,))

    # ---- assignment pieces
    def asg_parts(self, e):
        """statements implementing assignment e; returns (stmts, target)"""
        op, lhs, rhs = e[1], e[2], e[3]
        stmts = []
        if rhs[0] == "asg":
            s2, t2 = self.asg_parts(rhs)
            stmts += s2
            rv, rk = t2, "any"
            r_is_code = True
        else:
            r_is_code = False
        pre, tgt, tk, rkind = self.lval(lhs, cache=(op != "="))
        stmts += pre
        if r_is_code:
            v, vk = rv, rk
        else:
            v, vk = self.val(rhs) if op != "=" else self.ex(rhs)
        if op != "=":
            v, vk = self.arith(op[0], (tgt, tk or rkind), (v, vk))
        stmts.append("%s = %s" % (tgt, self.conv(v, vk, tk) if tk else self.val_code(v, vk)))
        return stmts, tgt

    def val_code(self, c, k):
        return "(%s and 1 or 0)" % c if k == "cond" else c

    def incdec_parts(self, e):
        op = "+" if e[1] == "++" else "-"
        pre, tgt, tk, rk = self.lval(e[2], cache=True)
        return pre, tgt, "%s = %s %s 1" % (tgt, tgt, op)

    # ---- expressions
    def ex(self, e):
        k = e[0]
        if k == "num":
            if e[2]:
                return flit(e[1]), "float"
            v = e[1]
            if v > 0x7FFFFFFFFFFFFFFF:
                return flit(v), "float"
            return str(v), "int"
        if k == "str":
            return lstr(e[1]), "str"
        if k == "bool":
            return ("1" if e[1] else "0"), "int"
        if k == "null":
            return "nil", "obj"
        if k == "this":
            return ("self" if self.has_self else "K.this"), "obj"
        if k == "super":
            return self.super_code(), "any"
        if k == "flag":
            return "__R__.flag(%s)" % lstr(e[1]), "cond"
        if k == "name":
            return self.name_ref(e[1])
        if k == "call":
            return self.call(e)
        if k == "idx":
            o, ok = self.ex(e[1])
            i, ik = self.val(e[2])
            if ik != "int":
                i = "ti(%s)" % i
            return "%s[%s]" % (pfx(o), i), "any"
        if k == "mem":
            o, ok = self.ex(e[1])
            return fa(pfx(o), e[2]), FIELD_KINDS.get(e[2], "any")
        if k == "un":
            op = e[1]
            if op == "!":
                return "(not %s)" % self.cond(e[2]), "cond"
            if op == "&":
                return self.ref(e[2])
            if op == "*":
                o, ok = self.ex(e[2])
                return "%s.v" % pfx(o), "any"
            v, vk = self.val(e[2])
            if op == "-":
                if v[:1].isdigit():
                    return "-" + v, vk
                return "(-%s)" % v, vk
            if op == "+":
                return v, vk
            if op == "~":
                return "(~%s)" % (v if vk == "int" else "ti(%s)" % v), "int"
        if k == "bin":
            return self.binop(e[1], e[2], e[3])
        if k == "asg":
            stmts, tgt = self.asg_parts(e)
            return "(function() %s; return %s end)()" % ("; ".join(stmts), tgt), "any"
        if k in ("post", "pre"):
            pre, tgt, upd = self.incdec_parts(e)
            if k == "pre":
                return "(function() %s; return %s end)()" % ("; ".join(pre + [upd]), tgt), "any"
            t = self.tmp("v")
            body = pre + ["local %s = %s" % (t, tgt), upd]
            return "(function() %s; return %s end)()" % ("; ".join(body), t), "any"
        if k == "new":
            tname, al, size = e[1], e[2], e[3]
            if size is not None:
                s, sk = self.val(size)
                return "__R__.newarr(%s, %s)" % (lstr(tname), s), "obj"
            a = self.args(al or [])
            return "__R__.new(%s%s)" % (lstr(tname), ", " + a if a else ""), "obj"
        if k == "is":
            v, vk = self.val(e[1])
            return "__R__.is(%s, %s)" % (v, lstr(e[2])), "cond"
        raise CompileError("unknown expr %r" % (k,))

    def ref(self, e):
        # &x : structs/objects are already references
        c, kd = self.ex(e)
        if kd == "obj" and e[0] in ("name", "mem", "idx"):
            if e[0] == "name":
                loc = self.lookup(e[1])
                if loc and loc[2] is None:
                    return c, "obj"
            else:
                return c, "obj"
        try:
            pre, tgt, tk, rk = self.lval(e, cache=False)
        except CompileError:
            return c, kd
        return "__R__.ref(function() return %s end, function(__v) %s = __v end)" % (tgt, tgt), "obj"

    def arith(self, op, a, b):
        av, ak = a
        bv, bk = b
        num = ("int", "float")
        if op == "+":
            if ak == "str" or bk == "str":
                return "__R__.cat(%s, %s)" % (av, bv), "str"
            if ak in num and bk in num:
                return "(%s + %s)" % (av, bv), ("int" if ak == bk == "int" else "float")
            return "__R__.add(%s, %s)" % (av, bv), "any"
        if op in ("-", "*"):
            kk = "int" if ak == bk == "int" else ("float" if "float" in (ak, bk) else "any")
            return "(%s %s %s)" % (av, op, bv), kk
        if op == "/":
            if ak == "float" or bk == "float":
                return "(%s / %s)" % (av, bv), "float"
            return "div(%s, %s)" % (av, bv), ("int" if ak == bk == "int" else "any")
        if op == "%":
            return "mod(%s, %s)" % (av, bv), ("int" if ak == bk == "int" else "any")
        if op == "^":
            return "(%s ^ %s)" % (av, bv), "float"
        ti_a = av if ak == "int" else "ti(%s)" % av
        ti_b = bv if bk == "int" else "ti(%s)" % bv
        if op in ("&", "|", "<<"):
            return "(%s %s %s)" % (ti_a, {"&": "&", "|": "|", "<<": "<<"}[op], ti_b), "int"
        if op == ">>":
            return "__R__.shr(%s, %s)" % (av, bv), "int"
        raise CompileError("bad arith op " + op)

    def binop(self, op, a, b):
        if op in ("&&", "||"):
            return "(%s %s %s)" % (self.cond(a), "and" if op == "&&" else "or", self.cond(b)), "cond"
        if op in ("==", "!="):
            neg = op == "!="

            def zero(x):
                return x[0] == "null" or (x[0] == "num" and x[1] == 0)
            if zero(a) or zero(b):
                other = b if zero(a) else a
                ov, ok = self.val(other)
                if a[0] == "null" or b[0] == "null" or ok not in ("int", "float"):
                    return ("(not isnull(%s))" if neg else "isnull(%s)") % ov, "cond"
            av, ak = self.val(a)
            bv, bk = self.val(b)
            simple = ak in ("int", "float", "str") or bk in ("int", "float", "str")
            if simple:
                return "(%s %s %s)" % (av, "~=" if neg else "==", bv), "cond"
            return ("(not __R__.eq(%s, %s))" if neg else "__R__.eq(%s, %s)") % (av, bv), "cond"
        if op in ("<", ">", "<=", ">="):
            av, ak = self.val(a)
            bv, bk = self.val(b)
            return "(%s %s %s)" % (av, op, bv), "cond"
        return self.arith(op, self.val(a), self.val(b))

    def call(self, e):
        fn, al = e[1], e[2]
        u = self.u
        if fn[0] == "super":
            return self.super_code(al), "any"
        if fn[0] == "mem":
            o, ok = self.ex(fn[1])
            a = self.args(al)
            name = fn[2]
            if fn[1][0] == "this" and self.has_self and u.script_method(self.cls, name) \
                    and IDENT.match(name) and name not in LUA_KW:
                return "self:%s(%s)" % (name, a), self.ret_kind_method(name)
            return "mc(%s, %s%s)" % (o, lstr(name), ", " + a if a else ""), RET_KIND.get(name, "any")
        if fn[0] == "name":
            n = fn[1]
            loc = self.lookup(n)
            a = self.args(al)
            if loc:
                return "%s(%s)" % (loc[0], a), "any"
            # casts
            if n == "int" and len(al) == 1:
                v, vk = self.val(al[0])
                return (v if vk == "int" else "ti(%s)" % v), "int"
            if n in ("float", "fixed") and len(al) == 1:
                v, vk = self.val(al[0])
                return (v if vk == "float" else "tf(%s)" % v), "float"
            if n == "bool" and len(al) == 1:
                return "(%s and 1 or 0)" % self.cond(al[0]), "int"
            if n == "string" and len(al) == 1:
                return "__R__.str(%s)" % self.val(al[0])[0], "str"
            if n in u.script_free:
                f = u.d.funcs.get(n)
                rk = type_kind(*f["ret"]) if f and f["ret"] else "any"
                return "%s(%s)" % (self.gref(n), a), rk
            if self.has_self and u.script_method(self.cls, n) and IDENT.match(n) and n not in LUA_KW:
                return "self:%s(%s)" % (n, a), self.ret_kind_method(n)
            if u.is_enum_type(n) and len(al) == 1 and n not in FREE_BUILTINS:
                return "ti(%s)" % a, "int"
            if u.is_class(n) and len(al) == 1 and not (self.has_self and u.engine_method(self.cls, n)):
                return "__R__.cast(%s, %s)" % (lstr(n), a), "obj"
            if n == "EObjectClass" and len(al) == 1:
                return "ti(%s)" % a, "int"
            if self.has_self:
                if n in FREE_BUILTINS and not u.engine_method(self.cls, n) and n not in ALL_ENGINE_METHODS:
                    return "%s(%s)" % (fa("F", n), a), RET_KIND.get(n, "any")
                if not (n in FREE_BUILTINS or u.engine_method(self.cls, n)):
                    u.unres_calls[n] += 1
                return "call(self, %s%s)" % (lstr(n), ", " + a if a else ""), RET_KIND.get(n, "any")
            if n not in FREE_BUILTINS:
                u.unres_calls[n] += 1
            return "%s(%s)" % (fa("F", n), a), RET_KIND.get(n, "any")
        c, ck = self.ex(fn)
        return "%s(%s)" % (pfx(c), self.args(al)), "any"

    def ret_kind_method(self, name):
        for c in self.u.chain(self.cls):
            fl = self.u.d.methods.get((c, name))
            if fl:
                r = fl[0]["ret"]
                return type_kind(*r) if r else "any"
        return "any"

    # ---- statements
    def block(self, stmts):
        n = len(stmts)
        for i, s in enumerate(stmts):
            self.stmt(s, last=(i == n - 1))

    def stmt_line(self, code):
        if code.startswith("("):
            code = ";" + code
        self.emit(code)

    def stmt(self, s, last=False):
        k = s[0]
        if k == "block":
            if not s[1]:
                return
            self.emit("do")
            self.ind += 1
            self.push()
            self.block(s[1])
            self.pop()
            self.ind -= 1
            self.emit("end")
        elif k == "if":
            self.emit("if %s then" % self.cond(s[1]))
            self.sub(s[2])
            el = s[3]
            while el is not None:
                if el[0] == "if":
                    self.emit("elseif %s then" % self.cond(el[1]))
                    self.sub(el[2])
                    el = el[3]
                elif el[0] == "block" and len(el[1]) == 1 and el[1][0][0] == "if":
                    el = el[1][0]
                    self.emit("elseif %s then" % self.cond(el[1]))
                    self.sub(el[2])
                    el = el[3]
                else:
                    self.emit("else")
                    self.sub(el)
                    el = None
            self.emit("end")
        elif k == "while":
            self.loop(None, s[1], None, s[2])
        elif k == "for":
            self.emit("do")
            self.ind += 1
            self.push()
            if s[1] is not None:
                self.stmt(s[1])
            self.loop(None, s[2], s[3], s[4])
            self.pop()
            self.ind -= 1
            self.emit("end")
        elif k == "ret":
            if s[1] is None:
                code = "return"
            else:
                code = "return " + self.val(s[1])[0]
            self.emit(code if last else "do %s end" % code)
        elif k == "break":
            self.emit("break")
        elif k == "cont":
            if not self.loops:
                self.emit("-- continue outside loop")
                return
            self.loops[-1][1] = True
            self.emit("goto %s" % self.loops[-1][0])
        elif k == "decl":
            (base, ptr), decls = s[1], s[2]
            for (n, dims, init, extra) in decls:
                p = ptr + extra
                kind = type_kind(base, p, len(dims))
                tkind = kind if kind in ("int", "float") else None
                if dims:
                    ds = ", ".join(self.val(d)[0] for d in dims)
                    v = "__R__.arr({%s}, %s)" % (ds, self.default(base, p))
                    if init is not None:
                        v = self.val(init)[0]
                elif init is not None:
                    c, ck = self.ex(init)
                    v = self.conv(c, ck, tkind) if tkind else self.val_code(c, ck)
                else:
                    v = self.default(base, p)
                lname = self.declare(n, kind, None if dims else tkind)
                self.emit("local %s = %s" % (lname, v))
        elif k == "local":
            for (n, init) in s[1]:
                v = self.val(init)[0] if init is not None else "0"
                lname = self.declare(n, "any", None)
                self.emit("local %s = %s" % (lname, v))
        elif k == "expr":
            self.expr_stmt(s[1])
        elif k == "delete":
            self.emit("__R__.delete(%s)" % self.val(s[1])[0])
        elif k == "flagdef":
            self.emit("__R__.setflag(%s)" % lstr(s[1]))
        else:
            raise CompileError("unknown stmt %r" % (k,))

    def default(self, base, ptr):
        if ptr:
            return "nil"
        if base in ("int", "bool") or re.match(r"E[A-Z]", base) or base in self.u.d.enums:
            return "0"
        if base in ("fixed", "float"):
            return "0.0"
        if base == "string":
            return '""'
        if base == "void":
            return "nil"
        return "__R__.struct(%s)" % lstr(base)

    def expr_stmt(self, e):
        k = e[0]
        if k == "asg":
            stmts, tgt = self.asg_parts(e)
            if len(stmts) > 1 and any(x.startswith("local ") for x in stmts):
                self.emit("do")
                for x in stmts:
                    self.emit("  " + x)
                self.emit("end")
            else:
                for x in stmts:
                    self.stmt_line(x)
            return
        if k in ("post", "pre"):
            pre, tgt, upd = self.incdec_parts(e)
            if pre:
                self.emit("do %s; %s end" % ("; ".join(pre), upd))
            else:
                self.stmt_line(upd)
            return
        if k == "super":
            self.stmt_line(self.super_code())
            return
        c, ck = self.ex(e)
        if ck != "cond" and c.endswith(")") and re.match(r"[A-Za-z_(]", c) and not c.startswith("(not ") \
                and k == "call":
            self.stmt_line(c)
        else:
            self.emit("local _ = %s" % c)

    def sub(self, s):
        self.ind += 1
        self.push()
        if s[0] == "block":
            self.block(s[1])
        else:
            self.stmt(s, last=True)
        self.pop()
        self.ind -= 1

    def loop(self, init, c, step, body):
        cond = "true" if c is None else self.cond(c)
        self.nlab += 1
        lab = "cont_%d" % self.nlab
        self.loops.append([lab, False])
        self.emit("while %s do" % cond)
        self.ind += 1
        mark = len(self.lines)
        self.ind += 1
        self.push()
        if body[0] == "block":
            self.block(body[1])
        else:
            self.stmt(body)
        self.pop()
        self.ind -= 1
        used = self.loops.pop()[1]
        if used:
            self.lines.insert(mark, "  " * self.ind + "do")
            self.emit("end")
            self.emit("::%s::" % lab)
        else:
            # undo the extra indentation level
            for j in range(mark, len(self.lines)):
                if self.lines[j].startswith("  "):
                    self.lines[j] = self.lines[j][2:]
        if step is not None:
            self.expr_stmt(step)
        self.ind -= 1
        self.emit("end")

    # ---- whole function
    def compile(self, params):
        """params: list of ((base, ptr), pname); returns list of lines (body)"""
        pl = []
        conv = []
        for i, ((base, ptr), pn) in enumerate(params):
            n = pn or "_p%d" % (i + 1)
            kind = type_kind(base, ptr)
            tkind = kind if kind in ("int", "float") else None
            lname = self.declare(n, kind, tkind)
            pl.append(lname)
            if tkind == "int":
                conv.append("%s = ti(%s)" % (lname, lname))
            elif tkind == "float":
                conv.append("%s = tf(%s)" % (lname, lname))
        self.pnames = pl
        for c in conv:
            self.emit(c)
        body = self.f["body"]
        self.block(body[1] if body[0] == "block" else [body])
        return pl


# ---------------------------------------------------------------- file codegen
HEADER = ("local __R__, __P__, __G__ = ...\n"
          "local T, ti, tf, div, mod, isnull, K, F, call, mc = __R__.T, __R__.ti, __R__.tf, __R__.div, "
          "__R__.mod, __R__.isnull, __R__.K, __R__.F, __R__.call, __R__.mc\n")


def compile_file(unit, key):
    ast = parsed(key)
    script = os.path.splitext(os.path.basename(key))[0]
    scls = script_classes(ast, script)
    out = [HEADER, "__P__:file(%s)\n" % lstr(key)]
    gnames = []
    ginit = []
    errors = []
    ginit_fn = Fn(unit, {"body": ("block", []), "params": []}, False, False, None)
    ginit_fn.ind = 1
    for node in ast:
        kind = node[0]
        if kind == "require":
            out.append("__P__:require({%s})\n" % ", ".join(lstr(x) for x in node[1]))
        elif kind == "flag":
            out.append("__P__:defflag(%s)\n" % lstr(node[1]))
        elif kind == "classdecl":
            out.append("__P__:class(%s, %s)\n" % (lstr(node[1]), lstr(node[2])))
        elif kind == "enum":
            for m, e in node[2]:
                if m in unit.consts:
                    v = unit.consts[m]
                    out.append("__G__[%s] = %s\n" % (lstr(m), v if isinstance(v, int) else flit(v)))
                elif e is not None:
                    try:
                        c = ginit_fn.val(e)[0]
                        ginit.append("__G__[%s] = %s" % (lstr(m), c))
                    except CompileError as ex:
                        errors.append("%s: enum %s: %s" % (key, m, ex))
        elif kind == "gdecl":
            (base, ptr), decls = node[1], node[2]
            for (n, dims, init, extra) in decls:
                gnames.append(n)
                p = ptr + extra
                try:
                    if dims:
                        ds = ", ".join(ginit_fn.val(d)[0] for d in dims)
                        v = "__R__.arr({%s}, %s)" % (ds, ginit_fn.default(base, p))
                    elif init is not None:
                        c, ck = ginit_fn.ex(init)
                        tk = type_kind(base, p)
                        v = ginit_fn.conv(c, ck, tk if tk in ("int", "float") else None) \
                            if tk in ("int", "float") else ginit_fn.val_code(c, ck)
                    else:
                        v = ginit_fn.default(base, p)
                    if v != "nil":
                        ginit.append("%s = %s" % (fa("__G__", n), v))
                except CompileError as ex:
                    errors.append("%s:%d: gvar %s: %s" % (key, node[3], n, ex))
    if gnames:
        out.append("__P__:gvars({%s})\n" % ", ".join(lstr(n) for n in gnames))
    if ginit:
        out.append("__P__:ginit(function()\n" + "".join("  %s\n" % x for x in ginit) + "end)\n")
    nfun = 0
    for node in ast:
        if node[0] != "func":
            continue
        f = node[1]
        if f["body"] is None:
            continue
        cls, name, ov = f["cls"], f["name"], f["override"]
        loc = "-- %s:%d %s%s%s\n" % (os.path.basename(key), f["line"], "override " if ov else "",
                                    cls + "::" if cls else "", name)
        if cls is None:
            if ov:
                head = "__P__:override(nil, %s, function(self, super%%s)" % lstr(name)
                hs, sup, ctx = False, True, None
            else:
                head = "__P__:func(%s, function(%%s)" % lstr(name)
                hs, sup, ctx = False, False, None
            tail = "end)"
        elif cls == name:
            head = "__P__:ctor(%s, function(self, super%%s)" % lstr(cls)
            tail = "end, %s)" % ("true" if ov else "false")
            hs, sup, ctx = True, True, cls
        elif cls in scls and not ov:
            if name in ENTRY_NAMES:
                head = "__P__:entry(%s, %s, function(%%s)" % (lstr(cls), lstr(name))
            else:
                head = "__P__:func(%s, function(%%s)" % lstr(name)
            tail = "end)"
            hs, sup, ctx = False, False, None
        elif ov:
            head = "__P__:override(%s, %s, function(self, super%%s)" % (lstr(cls), lstr(name))
            tail = "end)"
            hs, sup, ctx = True, True, cls
        else:
            head = "__P__:method(%s, %s, function(self, super%%s)" % (lstr(cls), lstr(name))
            tail = "end)"
            hs, sup, ctx = True, True, cls
        fn = Fn(unit, f, hs, sup, ctx)
        try:
            pl = fn.compile(f["params"])
        except (CompileError, RecursionError) as ex:
            errors.append("%s:%d: %s: %s" % (key, f["line"], name, ex))
            continue
        ps = ", ".join(pl)
        if sup or hs:
            ps = (", " + ps) if ps else ""
        out.append(loc)
        out.append(head % ps + "\n")
        out.append("\n".join(fn.lines) + ("\n" if fn.lines else ""))
        out.append(tail + "\n")
        nfun += 1
    return "".join(out), errors


# ---------------------------------------------------------------- drivers
_LUA = None


def lua_check(src, name):
    global _LUA
    if _LUA is None:
        from lupa.lua53 import LuaRuntime
        _LUA = LuaRuntime()
        _LUA.execute("function __chk(s, n) local f, e = load(s, n, 't', {}); return e end")
    return _LUA.globals().__chk(src, name)


def build_unit(files, cache={}):
    key = tuple(files)
    if key not in cache:
        own, full, libs = package_decls(files)
        all_files = [f for _, fl in libs for f in fl] + list(files)
        cache[key] = (Unit(full, all_files), libs)
    return cache[key]


def compile_pkg(pkg, files, outdir, check, report):
    unit, libs = build_unit(files)
    res = {"pkg": pkg, "files": [], "errors": [], "luaerr": [], "libs": [n for n, _ in libs]}
    pdir = os.path.join(outdir, pkg)
    os.makedirs(pdir, exist_ok=True)
    for k in files:
        try:
            src, errs = compile_file(unit, k)
        except (CompileError, PXError, RecursionError) as ex:
            res["errors"].append("%s: %s" % (k, ex))
            continue
        res["errors"] += errs
        fn = os.path.splitext(os.path.basename(k))[0] + ".lua"
        with open(os.path.join(pdir, fn), "w", encoding="ascii", newline="\n") as fo:
            fo.write(src)
        res["files"].append(fn)
        if check:
            le = lua_check(src, "@" + k)
            if le:
                res["luaerr"].append(str(le))
    with open(os.path.join(pdir, "pxchunks.json"), "w") as fo:
        json.dump({"pkg": pkg, "libs": res["libs"], "chunks": res["files"]}, fo, indent=1)
    report["unres_calls"].update(unit.unres_calls)
    report["unres_names"].update(unit.unres_names)
    unit.unres_calls.clear()
    unit.unres_names.clear()
    return res


def main(argv):
    outdir = os.path.join(HERE, "testout", "lua")
    check = "--check" in argv
    if "--out" in argv:
        outdir = argv[argv.index("--out") + 1]
    report = {"unres_calls": collections.Counter(), "unres_names": collections.Counter()}
    results = []
    pk = packages()
    if "--all" in argv or "--pkg" in argv:
        if "--all" in argv:
            sel = sorted(pk)
        else:
            sel = [a for a in argv[argv.index("--pkg") + 1:] if not a.startswith("--")]
        # libs
        libnames = set()
        for p in sel:
            try:
                _, libs = build_unit(pk[p])
            except Exception as ex:
                results.append({"pkg": p, "files": [], "errors": ["decl: %s" % ex], "luaerr": []})
                continue
            for n, fl in libs:
                if fl and fl[0].startswith("@lib/"):
                    libnames.add(n)
        for n in sorted(libnames):
            results.append(compile_pkg("@lib/" + n, lib_files(n), outdir, check, report))
        for p in sel:
            if p not in pk:
                print("no package", p)
                continue
            results.append(compile_pkg(p, pk[p], outdir, check, report))
    else:
        for path in [a for a in argv if not a.startswith("--")]:
            key = None
            for k in corpus():
                if k.endswith("/" + os.path.basename(path)) or k == path:
                    key = k
                    break
            if key is None:
                print("not in corpus:", path)
                continue
            p = key.split("/")[0]
            files = lib_files(key.split("/")[1][:-4]) if p == "@lib" else pk[p]
            results.append(compile_pkg(p if p != "@lib" else key[:-4], files, outdir, check, report))
    nerr = sum(len(r["errors"]) for r in results)
    nlua = sum(len(r["luaerr"]) for r in results)
    nfiles = sum(len(r["files"]) for r in results)
    with open(os.path.join(HERE, "pxc2lua_report.txt"), "w", encoding="utf-8") as fo:
        fo.write("units %d files %d compile_errors %d lua_errors %d\n" % (len(results), nfiles, nerr, nlua))
        for r in results:
            for x in r["errors"]:
                fo.write("ERR %s\n" % x)
            for x in r["luaerr"]:
                fo.write("LUA %s\n" % x)
        fo.write("\n== unresolved calls\n")
        for n, c in report["unres_calls"].most_common(300):
            fo.write("%6d %s\n" % (c, n))
        fo.write("\n== unresolved names\n")
        for n, c in report["unres_names"].most_common(300):
            fo.write("%6d %s\n" % (c, n))
    print("units %d files %d compile_errors %d lua_errors %d" % (len(results), nfiles, nerr, nlua))


if __name__ == "__main__":
    sys.setrecursionlimit(5000)
    main(sys.argv[1:])
