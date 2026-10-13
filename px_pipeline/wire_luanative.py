"""Wire LuaNative into dllmain.cpp and CMakeLists.txt; normalise new files to CRLF."""
CRLF = chr(13) + chr(10)
LF = chr(10)
R = r"C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm"


def rd(p):
    return open(p, encoding="utf-8", newline="").read()


def wr(p, s):
    open(p, "w", encoding="utf-8", newline="").write(s)


for f in [r"\src\LuaNative.cpp", r"\src\LuaNative.h"]:
    s = rd(R + f).replace(CRLF, LF).replace(LF, CRLF)
    wr(R + f, s)

p = R + r"\src\dllmain.cpp"
s = rd(p)
nl = CRLF if CRLF in s else LF
if "LuaNative" not in s:
    a = '#include "Hud.h"' + nl
    assert a in s
    s = s.replace(a, a + '#include "LuaNative.h"' + nl, 1)
    a = "\tHud::install();" + nl
    assert a in s
    s = s.replace(a, a + "\tLuaNative::install();" + nl, 1)
    wr(p, s)

p = R + r"\CMakeLists.txt"
s = rd(p)
nl = CRLF if CRLF in s else LF
if "LuaNative" not in s:
    a = "        src/Lua.cpp src/Lua.h" + nl
    assert a in s
    s = s.replace(a, a + "        src/LuaNative.cpp src/LuaNative.h" + nl, 1)
    wr(p, s)
print("ok")
