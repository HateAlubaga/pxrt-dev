import re
p='pxc2lua.py'
s=open(p,encoding='utf-8').read()
old="""                lname = self.declare(n, kind, None if dims else tkind)
                self.decl_stmt(lname, v)
        elif k == "local":"""
new="""                if self.has_self and len(self.scopes) == 1 and self.f.get("cls") \\
                        and self.f.get("cls") == self.f.get("name"):
                    # typed declarations at the top of a ctor are member fields
                    self.emit("self.%s = %s" % (ln(n), v))
                    continue
                lname = self.declare(n, kind, None if dims else tkind)
                self.decl_stmt(lname, v)
        elif k == "local":"""
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)