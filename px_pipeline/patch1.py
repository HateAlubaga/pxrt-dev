p = 'pxc2lua.py'
s = open(p, encoding='utf-8', newline='').read()


def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (a, s.count(a))
    s = s.replace(a, b)


rep('''CONST_PREFIXES = ("M_", "WS_", "OC_", "CT_", "DT_", "WCT_", "CM_", "LAYER_", "CMASK_", "TI_",
                  "EObjectClass")''', '''CONST_PREFIXES = ("M_", "WS_", "OC_", "CT_", "DT_", "WCT_", "CM_", "LAYER_", "CMASK_", "TI_",
                  "EObjectClass", "WT_", "AT_", "WAT_", "WAction_", "WExplode_")''')
rep('''        self.pnames = []

    # ---- scopes''', '''        self.pnames = []
        # Lua caps a function at 200 locals; huge PX functions keep their
        # variables in a table instead
        self.ndecl = 0

        def cnt(st):
            if st[0] == "decl":
                self.ndecl += len(st[2])
            elif st[0] == "local":
                self.ndecl += len(st[1])
        if f.get("body") is not None:
            walk_stmt(f["body"], cnt, lambda e: None)
        self.tbl = self.ndecl > 120
        self.ntbl = 0

    # ---- scopes''')
rep('''    def declare(self, n, kind, tkind):
        lname = ln(n)''', '''    def declare(self, n, kind, tkind, param=False):
        lname = ln(n)
        if self.tbl and not param:
            self.ntbl += 1
            lname = "__L.%s_%d" % (lname, self.ntbl)''')
rep('''                lname = self.declare(n, kind, None if dims else tkind)
                self.emit("local %s = %s" % (lname, v))''', '''                lname = self.declare(n, kind, None if dims else tkind)
                self.emit(("%s = %s" if self.tbl else "local %s = %s") % (lname, v))''')
rep('''                lname = self.declare(n, "any", None)
                self.emit("local %s = %s" % (lname, v))''', '''                lname = self.declare(n, "any", None)
                self.emit(("%s = %s" if self.tbl else "local %s = %s") % (lname, v))''')
rep('''            lname = self.declare(n, kind, tkind)
            pl.append(lname)''', '''            lname = self.declare(n, kind, tkind, param=True)
            pl.append(lname)''')
rep('''        self.pnames = pl
        for c in conv:''', '''        self.pnames = pl
        if self.tbl:
            self.emit("local __L = {}")
        for c in conv:''')
open(p, 'w', encoding='utf-8', newline='').write(s)
print("ok")
