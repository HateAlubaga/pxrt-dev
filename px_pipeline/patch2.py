p = 'pxc2lua.py'
s = open(p, encoding='utf-8', newline='').read()


def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (a, s.count(a))
    s = s.replace(a, b)


rep('''    def __init__(self, unit, f, has_self, has_super, cls):
        self.u = unit''', '''    def __init__(self, unit, f, has_self, has_super, cls, hoist=None):
        self.u = unit
        # PX locals outlive their block (`if(..){local w=..} if(w..)`): names
        # used after their block closed are hoisted to function scope
        self.hoist = set(hoist or ())
        self.need_hoist = set()
        self.declared_ever = {}''')
rep('''        if self.tbl and not param:
            self.ntbl += 1
            lname = "__L.%s_%d" % (lname, self.ntbl)
        self.scopes[-1][n] = (lname, kind, tkind)
        return lname

    def lookup(self, n):
        for sc in reversed(self.scopes):
            if n in sc:
                return sc[n]
        return None''', '''        if n in self.hoist and not param:
            lname = ("__L.__h_%s" if self.tbl else "__h_%s") % lname
        elif self.tbl and not param:
            self.ntbl += 1
            lname = "__L.%s_%d" % (lname, self.ntbl)
        self.scopes[-1][n] = (lname, kind, tkind)
        if not param:
            self.declared_ever[n] = (lname, kind, tkind)
        return lname

    def decl_stmt(self, lname, v):
        if self.tbl or lname.startswith("__h_"):
            self.emit("%s = %s" % (lname, v))
        else:
            self.emit("local %s = %s" % (lname, v))

    def lookup(self, n):
        for sc in reversed(self.scopes):
            if n in sc:
                return sc[n]
        if n in self.declared_ever:
            if n in self.hoist:
                return self.declared_ever[n]
            self.need_hoist.add(n)
        return None''')
rep('''                lname = self.declare(n, kind, None if dims else tkind)
                self.emit(("%s = %s" if self.tbl else "local %s = %s") % (lname, v))''', '''                lname = self.declare(n, kind, None if dims else tkind)
                self.decl_stmt(lname, v)''')
rep('''                lname = self.declare(n, "any", None)
                self.emit(("%s = %s" if self.tbl else "local %s = %s") % (lname, v))''', '''                lname = self.declare(n, "any", None)
                self.decl_stmt(lname, v)''')
rep('''        if self.tbl:
            self.emit("local __L = {}")
        for c in conv:''', '''        if self.tbl:
            self.emit("local __L = {}")
        elif self.hoist:
            self.emit("local %s" % ", ".join("__h_" + ln(n) for n in sorted(self.hoist)))
        for c in conv:''')
rep('''        fn = Fn(unit, f, hs, sup, ctx)
        try:
            pl = fn.compile(f["params"])
        except (CompileError, RecursionError) as ex:''', '''        try:
            hoist = set()
            for _ in range(4):
                fn = Fn(unit, f, hs, sup, ctx, hoist)
                pl = fn.compile(f["params"])
                if not (fn.need_hoist - hoist):
                    break
                hoist |= fn.need_hoist
        except (CompileError, RecursionError) as ex:''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print("ok")
