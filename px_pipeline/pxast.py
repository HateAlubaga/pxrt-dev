"""ProjectX (.pxc) tokenizer + recursive-descent parser -> tuple AST.

Expressions:
  ('num', value, is_float)  ('str', s)  ('name', id)  ('flag', NAME)
  ('this',) ('super',) ('null',) ('bool', v)
  ('call', fn_expr, [args])  ('idx', obj, idx)  ('mem', obj, name)
  ('un', op, e)  op in - ! ~ & * +
  ('bin', op, a, b)  ('asg', op, target, value)  op in = += -= *= /=
  ('post', op, e)  ('pre', op, e)
  ('new', typename, args_or_None, arraysize_or_None)
  ('is', e, typename)
Statements:
  ('block', [stmts]) ('if', c, t, e) ('while', c, b) ('for', init, cond, step, body)
  ('ret', e) ('break',) ('cont',) ('decl', type, [(name, arrdims, init)], line)
  ('local', [(name, init)], line) ('expr', e, line) ('delete', e) ('empty',)
  type = (basename, ptrdepth)
Top level:
  ('require', [names]) ('flag', NAME) ('enum', name, [(member, expr_or_None)])
  ('classdecl', name, base) ('gdecl', type, [(name, arrdims, init)])
  ('func', dict(override, ret, cls, name, params=[(type,name)], body, line, proto))
"""
import re

BASETYPES = {"int", "fixed", "float", "bool", "string", "void"}
KEYWORDS = {"if", "else", "while", "for", "return", "break", "continue", "new", "delete",
            "local", "override", "require", "enum", "this", "super", "is", "true", "false",
            "NullObj"}


class PXError(Exception):
    pass


TOK_RE = re.compile(r"""
  (?P<ws>[ \t\r\n]+)
| (?P<lc>//[^\n]*)
| (?P<bc>/\*.*?(\*/|\Z))
| (?P<dnum>\d+[A-Za-z_][A-Za-z0-9_]*)
| (?P<num>\d+\.\d*|\d+)
| (?P<hex>\$[0-9A-Fa-f]+(?![A-Za-z0-9_]))
| (?P<str>"[^"\n]*")
| (?P<flag>\#[A-Za-z_][A-Za-z0-9_]*)
| (?P<id>[A-Za-z_][A-Za-z0-9_]*)
| (?P<op>->|::|\+\+|--|\+=|-=|\*=|/=|==|!=|<=|>=|&&|\|\||<<|>>|[-+*/%=<>!&|^~()\[\]{},;.:?])
""", re.S | re.X)


def tokenize(text):
    """Returns list of (kind, value, line). Lines starting with $ (editor blocks) are skipped."""
    # blank out editor lines: first non-space char '$' followed by a letter word that is not pure hex
    lines = text.split("\n")
    for i, l in enumerate(lines):
        s = l.lstrip()
        if s.startswith("$") and not re.match(r"\$[0-9A-Fa-f]+(?![A-Za-z0-9_])", s):
            lines[i] = ""
    text = "\n".join(lines)
    toks = []
    pos = 0
    line = 1
    n = len(text)
    while pos < n:
        m = TOK_RE.match(text, pos)
        if not m:
            c = text[pos]
            # stray chars (e.g. latin-1 garbage, '\\', '@', '`') -> skip but record
            toks.append(("bad", c, line))
            if c == "\n":
                line += 1
            pos += 1
            continue
        kind = m.lastgroup
        v = m.group(kind)
        if kind in ("ws", "lc", "bc"):
            line += v.count("\n")
        elif kind == "num":
            toks.append(("num", v, line))
        elif kind == "hex":
            toks.append(("hex", v, line))
        elif kind == "str":
            toks.append(("str", v[1:-1], line))
        elif kind == "flag":
            toks.append(("flag", v[1:], line))
        elif kind in ("id", "dnum"):   # dnum: identifier starting with a digit (30seconds, 1pointers, 1s)
            toks.append(("id", v, line))
        else:
            toks.append(("op", v, line))
        pos = m.end()
    toks.append(("eof", None, line))
    return toks


class Parser:
    def __init__(self, text, fname="?"):
        self.t = [x for x in tokenize(text) if x[0] != "bad"]
        self.bad = [x for x in tokenize(text) if x[0] == "bad"] if False else []
        self.i = 0
        self.fname = fname
        self.known_types = set()   # class / enum names declared or seen (helps decl detection)

    # ---- token helpers
    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def at(self, v, k=0):
        tk = self.peek(k)
        return tk[0] in ("op", "id") and tk[1] == v

    def next(self):
        tk = self.t[self.i]
        if self.i < len(self.t) - 1:
            self.i += 1
        return tk

    def expect(self, v):
        tk = self.next()
        if tk[1] != v:
            raise PXError("%s:%d: expected %r got %r" % (self.fname, tk[2], v, tk[1]))
        return tk

    def accept(self, v):
        if self.at(v):
            self.next()
            return True
        return False

    def ident(self):
        tk = self.next()
        if tk[0] != "id":
            raise PXError("%s:%d: expected identifier got %r" % (self.fname, tk[2], tk[1]))
        return tk[1]

    def err(self, msg):
        tk = self.peek()
        raise PXError("%s:%d: %s (at %r)" % (self.fname, tk[2], msg, tk[1]))

    # ---- top level
    def parse_file(self):
        out = []
        while self.peek()[0] != "eof":
            r = self.toplevel()
            if r is not None:
                out.extend(r if isinstance(r, list) else [r])
        return out

    def toplevel(self):
        tk = self.peek()
        if tk[0] == "op" and tk[1] == ";":
            self.next()
            return None
        if tk[0] == "op" and tk[1] == "}":   # stray closing brace (seen in a few sloppy files)
            self.next()
            return None
        if tk[0] == "flag":
            self.next()
            self.accept(";")
            return ("flag", tk[1])
        if tk[0] != "id":
            self.err("unexpected token at top level")
        if tk[1] == "require":
            self.next()
            names = [self.ident()]
            while self.accept(","):
                names.append(self.ident())
            if not self.accept(";"):
                self.accept(":")   # 'require a, b:' (typo for ';') in weapon_air_911
            return ("require", names)
        if tk[1] == "enum":
            self.next()
            name = self.ident()
            self.known_types.add(name)
            self.expect("=")
            self.expect("(")
            mem = []
            while not self.at(")"):
                m = self.ident()
                v = None
                if self.accept("="):
                    v = self.expr()
                mem.append((m, v))
                if not self.accept(","):
                    break
            self.expect(")")
            self.accept(";")
            return ("enum", name, mem)
        # class decl  Name : Base
        if self.peek(1)[0] == "op" and self.peek(1)[1] == ":" and self.peek(2)[0] == "id":
            name = self.ident()
            self.next()
            base = self.ident()
            self.known_types.add(name)
            self.accept(";")
            return ("classdecl", name, base)
        line = tk[2]
        override = False
        if tk[1] == "override":
            self.next()
            override = True
        # collect header tokens up to '(' or ';' or '=' or '['  (function vs declaration)
        j = self.i
        hdr = []
        while True:
            t2 = self.t[j]
            if t2[0] == "id" or (t2[0] == "op" and t2[1] in ("*", "::", ",")):
                if t2[0] == "op" and t2[1] == ",":
                    break
                hdr.append(t2)
                j += 1
                continue
            break
        stop = self.t[j]
        if stop[0] == "op" and stop[1] == "(":
            return self.funcdef(override, line)
        if override:
            self.err("override without function")
        # global declaration
        typ = self.type_spec()
        decls = self.declarators(typ)
        self.accept(";")
        return ("gdecl", typ, decls, line)

    def type_spec(self):
        base = self.ident()
        p = 0
        while self.accept("*"):
            p += 1
        return (base, p)

    def declarators(self, typ):
        decls = []
        while True:
            extra = 0
            while self.accept("*"):
                extra += 1
            name = self.ident()
            dims = []
            while self.accept("["):
                dims.append(self.expr())
                self.expect("]")
            init = None
            if self.accept("="):
                init = self.expr()
            decls.append((name, dims, init, extra))
            if not self.accept(","):
                break
        return decls

    def funcdef(self, override, line):
        # header: [ret [*]] [Cls ::] Name ( params )
        toks = []
        while not self.at("("):
            toks.append(self.next())
        cls = None
        if any(t[1] == "::" for t in toks):
            k = max(idx for idx, t in enumerate(toks) if t[1] == "::")
            cls = toks[k - 1][1]
            name = toks[k + 1][1]
            rett = toks[:k - 1]
        else:
            name = toks[-1][1]
            rett = toks[:-1]
        ret = None
        if rett:
            base = [t for t in rett if t[0] == "id"]
            ret = (base[0][1] if base else "void", sum(1 for t in rett if t[1] == "*"))
        self.expect("(")
        params = []
        while not self.at(")"):
            ptyp = self.type_spec()
            pname = None
            if self.peek()[0] == "id":
                pname = self.ident()
            while self.accept("["):
                self.accept("]")
                ptyp = (ptyp[0], ptyp[1] + 1)
            params.append((ptyp, pname))
            if not self.accept(","):
                break
        self.expect(")")
        body = None
        proto = False
        if self.at("{"):
            body = self.block()
        else:
            self.accept(";")
            proto = True
        self.accept(";")
        return ("func", dict(override=override, ret=ret, cls=cls, name=name, params=params,
                             body=body, line=line, proto=proto))

    # ---- statements
    def block(self):
        self.expect("{")
        st = []
        while not self.at("}"):
            if self.peek()[0] == "eof":
                return ("block", st)   # missing final '}' at end of file (script_agility): closed implicitly
            s = self.stmt()
            if s is not None:
                st.append(s)
        self.expect("}")
        return ("block", st)

    def is_decl_start(self):
        t0 = self.peek()
        if t0[0] != "id":
            return False
        if t0[1] in BASETYPES:
            return True
        if t0[1] in KEYWORDS:
            return False
        # IDENT IDENT  (followed by = ; , [ )
        k = 1
        while self.peek(k)[0] == "op" and self.peek(k)[1] == "*":
            k += 1
        t1 = self.peek(k)
        if t1[0] != "id" or t1[1] in KEYWORDS:
            return False
        t2 = self.peek(k + 1)
        return t2[0] == "op" and t2[1] in ("=", ";", ",", "[")

    def stmt(self):
        tk = self.peek()
        line = tk[2]
        if tk[0] == "op":
            if tk[1] == "{":
                return self.block()
            if tk[1] == ";":
                self.next()
                return None
        if tk[0] == "flag" and self.peek(1)[1] == ";":
            self.next()
            self.next()
            return ("flagdef", tk[1])
        if tk[0] == "id":
            v = tk[1]
            if v == "if":
                self.next()
                self.expect("(")
                c = self.expr()
                self.expect(")")
                th = self.stmt_or_empty()
                el = None
                if self.accept("else"):
                    el = self.stmt_or_empty()
                return ("if", c, th, el)
            if v == "while":
                self.next()
                self.expect("(")
                c = self.expr()
                self.expect(")")
                return ("while", c, self.stmt_or_empty())
            if v == "for":
                self.next()
                self.expect("(")
                init = None
                if not self.at(";"):
                    if self.at("local"):
                        init = self.local_stmt()
                    elif self.is_decl_start():
                        init = self.decl_stmt(need_semi=False)
                    else:
                        init = ("expr", self.expr(), line)
                self.expect(";")
                cond = None if self.at(";") else self.expr()
                self.expect(";")
                step = None if self.at(")") else self.expr()
                self.expect(")")
                return ("for", init, cond, step, self.stmt_or_empty())
            if v == "return":
                self.next()
                e = None
                if not self.at(";") and not self.at("}"):
                    e = self.expr()
                self.accept(";")
                return ("ret", e)
            if v == "break":
                self.next()
                self.accept(";")
                return ("break",)
            if v == "continue":
                self.next()
                self.accept(";")
                return ("cont",)
            if v == "delete":
                self.next()
                e = self.expr()
                self.accept(";")
                return ("delete", e)
            if v == "local":
                s = self.local_stmt()
                self.accept(";")
                return s
            if self.is_decl_start():
                return self.decl_stmt()
        e = self.expr()
        while self.accept(")"):
            pass   # stray ')' after a complete call (f(a));  seen in published scripts); ignored
        if not self.accept(";"):
            # tolerate missing ';' before '}' or newline-separated statements
            if not self.at("}"):
                nt = self.peek()
                if nt[2] == line or nt[0] == "eof":
                    self.err("expected ;")
        return ("expr", e, line)

    def stmt_or_empty(self):
        if self.at(";"):
            self.next()
            return ("block", [])
        s = self.stmt()
        return s if s is not None else ("block", [])

    def local_stmt(self):
        line = self.peek()[2]
        self.expect("local")
        items = []
        while True:
            name = self.ident()
            init = None
            if self.accept("="):
                init = self.expr()
            items.append((name, init))
            if not self.accept(","):
                break
        return ("local", items, line)

    def decl_stmt(self, need_semi=True):
        line = self.peek()[2]
        typ = self.type_spec()
        decls = self.declarators(typ)
        if need_semi:
            self.accept(";")
        return ("decl", typ, decls, line)

    # ---- expressions
    def expr(self):
        return self.assign()

    def assign(self):
        lhs = self.logor()
        tk = self.peek()
        if tk[0] == "op" and tk[1] in ("=", "+=", "-=", "*=", "/="):
            self.next()
            rhs = self.assign()
            return ("asg", tk[1], lhs, rhs)
        return lhs

    def logor(self):
        a = self.logand()
        while self.at("||"):
            self.next()
            a = ("bin", "||", a, self.logand())
        return a

    def logand(self):
        a = self.bitor()
        while self.at("&&"):
            self.next()
            a = ("bin", "&&", a, self.bitor())
        return a

    def bitor(self):
        a = self.bitand()
        while self.at("|"):
            self.next()
            a = ("bin", "|", a, self.bitand())
        return a

    def bitand(self):
        a = self.equality()
        while self.at("&"):
            self.next()
            a = ("bin", "&", a, self.equality())
        return a

    def equality(self):
        a = self.relational()
        while self.peek()[0] == "op" and self.peek()[1] in ("==", "!="):
            op = self.next()[1]
            a = ("bin", op, a, self.relational())
        return a

    def relational(self):
        a = self.shift()
        while True:
            tk = self.peek()
            if tk[0] == "op" and tk[1] in ("<", ">", "<=", ">="):
                self.next()
                a = ("bin", tk[1], a, self.shift())
            elif tk[0] == "id" and tk[1] == "is":
                self.next()
                a = ("is", a, self.ident())
            else:
                return a

    def shift(self):
        a = self.additive()
        while self.peek()[0] == "op" and self.peek()[1] in ("<<", ">>"):
            op = self.next()[1]
            a = ("bin", op, a, self.additive())
        return a

    def additive(self):
        a = self.mult()
        while self.peek()[0] == "op" and self.peek()[1] in ("+", "-"):
            op = self.next()[1]
            a = ("bin", op, a, self.mult())
        return a

    def mult(self):
        a = self.power()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/", "%"):
            op = self.next()[1]
            a = ("bin", op, a, self.power())
        return a

    def power(self):
        a = self.unary()
        if self.at("^"):
            self.next()
            return ("bin", "^", a, self.power())
        return a

    def unary(self):
        tk = self.peek()
        if tk[0] == "op" and tk[1] in ("-", "!", "~", "&", "*", "+"):
            self.next()
            return ("un", tk[1], self.unary())
        if tk[0] == "op" and tk[1] in ("++", "--"):
            self.next()
            return ("pre", tk[1], self.unary())
        if tk[0] == "id" and tk[1] == "new":
            self.next()
            tname = self.ident()
            while self.accept("*"):
                pass
            args = None
            size = None
            if self.at("("):
                args = self.call_args()
            elif self.at("["):
                self.next()
                size = self.expr()
                self.expect("]")
            return self.postfix(("new", tname, args, size))
        return self.postfix(self.primary())

    def call_args(self):
        self.expect("(")
        args = []
        while not self.at(")"):
            args.append(self.expr())
            if not self.accept(","):
                break
        self.expect(")")
        return args

    def postfix(self, e):
        while True:
            tk = self.peek()
            if tk[0] != "op":
                return e
            v = tk[1]
            if v == "(":
                e = ("call", e, self.call_args())
            elif v == "[":
                self.next()
                ix = self.expr()
                self.expect("]")
                e = ("idx", e, ix)
            elif v in (".", "->"):
                self.next()
                e = ("mem", e, self.ident())
            elif v in ("++", "--"):
                self.next()
                e = ("post", v, e)
            else:
                return e

    def primary(self):
        tk = self.next()
        k, v = tk[0], tk[1]
        if k == "num":
            if "." in v:
                return ("num", float(v), True)
            return ("num", int(v), False)
        if k == "hex":
            return ("num", int(v[1:], 16), False)
        if k == "str":
            return ("str", v)
        if k == "flag":
            return ("flag", v)
        if k == "id":
            if v == "this":
                return ("this",)
            if v == "super":
                return ("super",)
            if v == "NullObj":
                return ("null",)
            if v == "true":
                return ("bool", True)
            if v == "false":
                return ("bool", False)
            return ("name", v)
        if k == "op" and v == "(":
            e = self.expr()
            self.expect(")")
            return e
        raise PXError("%s:%d: unexpected %r in expression" % (self.fname, tk[2], v))


def parse(text, fname="?"):
    return Parser(text, fname).parse_file()


if __name__ == "__main__":
    import sys, json, os, collections
    HERE = os.path.dirname(os.path.abspath(__file__))
    C = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))
    fails = collections.Counter()
    ok = 0
    out = []
    for k, t in C.items():
        try:
            parse(t, k)
            ok += 1
        except PXError as ex:
            out.append(str(ex))
        except RecursionError:
            out.append(k + ": recursion")
    with open(os.path.join(HERE, "parse_fail.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("ok", ok, "fail", len(out))
