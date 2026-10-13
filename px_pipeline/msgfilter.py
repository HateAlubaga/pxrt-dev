"""Static message-type filter for `override X::Message(sender, Type, size, data)`.

WA sends every task several messages per frame, and a loaded package set carries ~25 Message overrides per class, most
of which only act on one or two message types. For an override, `analyze` returns the set of names/numbers that
`Type` is compared against, when it can prove that for every other message type the override does nothing but call
its super once with unchanged arguments (all other code it would run is pure). The runtime then leaves the override
out of the chain for those types. Returns None when that cannot be proven (the override always runs).
"""

PURE_CALLS = {
    "GetCurrentWorm", "CheckName", "GetParameter", "KeyPressed", "KeyPressedNow", "IsKeyPressed", "IsKeyPressedB",
    "GetTeamColor", "abs", "fabs", "sqrt", "min", "max", "GetObject", "GetWeaponByIndex", "GetWeaponByName",
    "GetWeaponIndex", "GetHashObject", "IsHost", "IsReplay", "GetRandom_noSync",
}
CMP_OPS = ("==", "!=")


class Fail(Exception):
    pass


def analyze(f):
    params = [n for _, n in f["params"]]
    if len(params) < 2 or f["body"] is None:
        return None
    tname = params[1]
    try:
        consts = []
        _collect(f["body"], tname, consts)
        if not consts:
            return None
        sim = _Sim(tname, params)
        sim.block(f["body"][1] if f["body"][0] == "block" else [f["body"]])
        if sim.supers != 1 and not sim.done:
            return None
    except Fail:
        return None
    out = []
    for c in consts:
        if c not in out:
            out.append(c)
    return out


def _is_t(e, tname):
    return e[0] == "name" and e[1] == tname


def _collect(node, tname, consts):
    """every use of Type must be one side of == / != against a constant name or integer"""
    if not isinstance(node, tuple):
        if isinstance(node, list):
            for x in node:
                _collect(x, tname, consts)
        return
    if not node:
        return
    if node[0] == "bin" and node[1] in CMP_OPS and (_is_t(node[2], tname) or _is_t(node[3], tname)):
        other = node[3] if _is_t(node[2], tname) else node[2]
        if other[0] == "name":
            consts.append(other[1])
        elif other[0] == "num" and not other[2]:
            consts.append(int(other[1]))
        else:
            raise Fail()
        return
    if node[0] == "name" and node[1] == tname:
        raise Fail()   # Type used some other way (passed on, arithmetic, assigned...)
    if node[0] == "call" and node[1] == ("super",):
        return         # super(...) args are checked by _Sim
    for x in node[1:]:
        if isinstance(x, (tuple, list)):
            _collect(x, tname, consts)


class _Sim:
    def __init__(self, tname, params):
        self.t = tname
        self.params = params
        self.locals = set()
        self.supers = 0
        self.done = False

    # ---- expressions
    def pure(self, e):
        k = e[0]
        if k in ("num", "str", "name", "bool", "null", "this", "flag"):
            return True
        if k == "mem":
            return self.pure(e[1])
        if k == "idx":
            return self.pure(e[1]) and self.pure(e[2])
        if k == "un":
            return self.pure(e[2])
        if k == "bin":
            return self.pure(e[2]) and self.pure(e[3])
        if k == "is":
            return self.pure(e[1])
        if k == "call":
            fn = e[1]
            if not all(self.pure(a) for a in e[2]):
                return False
            if fn[0] == "name":
                return fn[1] in PURE_CALLS
            if fn[0] == "mem":
                return fn[2] in PURE_CALLS and self.pure(fn[1])
            return False
        return False

    def cond(self, e):
        """(value True/False/None, evaluated part pure)"""
        k = e[0]
        if k == "bin" and e[1] in CMP_OPS and (_is_t(e[2], self.t) or _is_t(e[3], self.t)):
            other = e[3] if _is_t(e[2], self.t) else e[2]
            return (e[1] == "!="), True if other[0] in ("name", "num") else False
        if k == "bin" and e[1] in ("&&", "||"):
            av, ap = self.cond(e[2])
            if not ap:
                return None, False
            if e[1] == "&&" and av is False:
                return False, True
            if e[1] == "||" and av is True:
                return True, True
            bv, bp = self.cond(e[3])
            if not bp:
                return None, False
            if e[1] == "&&":
                if bv is False:
                    return False, True
                return (True if (av is True and bv is True) else None), True
            if bv is True:
                return True, True
            return (False if (av is False and bv is False) else None), True
        if k == "un" and e[1] == "!":
            v, p = self.cond(e[2])
            return (None if v is None else not v), p
        return None, self.pure(e)

    # ---- statements
    def block(self, stmts, unknown=False):
        for s in stmts:
            if self.done:
                return
            self.stmt(s, unknown)

    def is_super(self, e):
        if e == ("super",):
            return True
        if e[0] == "call" and e[1] == ("super",):
            if len(e[2]) != len(self.params) or any(a != ("name", p) for a, p in zip(e[2], self.params)):
                raise Fail()
            return True
        return False

    def stmt(self, s, unknown):
        k = s[0]
        if k == "block":
            self.block(s[1], unknown)
        elif k == "empty":
            pass
        elif k == "decl":
            for d in s[2]:
                n, dims, init = d[0], d[1], d[2]
                if dims or (init is not None and not self.pure(init)):
                    raise Fail()
                self.locals.add(n)
        elif k == "local":
            for n, init in s[1]:
                if init is not None and not self.pure(init):
                    raise Fail()
                self.locals.add(n)
        elif k == "expr":
            e = s[1]
            if self.is_super(e):
                if unknown or self.supers:
                    raise Fail()
                self.supers = 1
            elif e[0] == "asg":
                if not (e[2][0] == "name" and e[2][1] in self.locals and self.pure(e[3])):
                    raise Fail()
            elif e[0] in ("post", "pre"):
                if not (e[2][0] == "name" and e[2][1] in self.locals):
                    raise Fail()
            elif not self.pure(e):
                raise Fail()
        elif k == "if":
            v, p = self.cond(s[1])
            if not p:
                raise Fail()
            if v is True:
                self.stmt(s[2], unknown)
            elif v is False:
                if s[3] is not None:
                    self.stmt(s[3], unknown)
            else:
                before = self.supers
                self.stmt(s[2], True)
                self.done = False
                if s[3] is not None:
                    self.stmt(s[3], True)
                self.done = False
                if self.supers != before:
                    raise Fail()
        elif k == "ret":
            if self.supers != 1 or (s[1] is not None and not self.pure(s[1])):
                raise Fail()
            if not unknown:
                self.done = True
        else:
            raise Fail()   # loops, delete, ...
