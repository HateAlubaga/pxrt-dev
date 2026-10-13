"""Add <Class>_CallOriginal_vtableN Lua bindings to CTask.h / CGameTask.h."""
import re
CRLF = chr(13) + chr(10)

SRC = r"C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\entities"

# ---- CTask.h
p = SRC + r"\CTask.h"
s = open(p, encoding="utf-8").read()
assert "callOriginalVt8" not in s
anchor = "\t\tstatic void registerCallbackVt18(t_vt18 cb) {vtable18_callbacks.push_back(cb);}\n"
assert anchor in s
funcs = """
\t\t// Call the unhooked implementation directly (PX `super` inside overrides).
\t\t// The Lua callback then returns nonzero so the original is not run twice.
\t\tstatic int callOriginalVt0(T * This, int a2) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int,int)>;
\t\t\treturn ((vPtr)vtable_original[0])(This, 0, a2);
\t\t}
\t\tstatic int callOriginalVt4(T * This, int heap) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int,int)>;
\t\t\treturn ((vPtr)vtable_original[1])(This, 0, heap);
\t\t}
\t\tstatic int callOriginalVt8(T * This, CTask * sender, int mtype, size_t size, DWORD data) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int,CTask*,Constants::TaskMessage, size_t, void*)>;
\t\t\treturn ((vPtr)vtable_original[2])(This, 0, sender, (Constants::TaskMessage)mtype, size, (void*)data);
\t\t}
\t\tstatic int callOriginalVtC(T * This, int a2, int a3, int a4) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int,int,int,int)>;
\t\t\treturn ((vPtr)vtable_original[3])(This, 0, a2, a3, a4);
\t\t}
\t\tstatic int callOriginalVt10(T * This, int a2, int a3, int a4) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int,int,int,int)>;
\t\t\treturn ((vPtr)vtable_original[4])(This, 0, a2, a3, a4);
\t\t}
\t\tstatic int callOriginalVt14(T * This, int a2) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int,int)>;
\t\t\treturn ((vPtr)vtable_original[5])(This, 0, a2);
\t\t}
\t\tstatic int callOriginalVt18(T * This) {
\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int)>;
\t\t\treturn ((vPtr)vtable_original[6])(This, 0);
\t\t}
"""
s = s.replace(anchor, anchor + funcs)
cast = '\tlua->set_function(#classname "_CastCTask", &castCTask<classname>);'
assert cast in s
binds = ""
for n in ["0", "4", "8", "C", "10", "14", "18"]:
    binds += '\tlua->set_function(#classname "_CallOriginal_vtable%s", &CTask_vtableHooks<classname>::callOriginalVt%s); \\\n' % (n, n)
s = s.replace(cast, binds + cast)
open(p, "w", encoding="utf-8", newline="").write(s)

# ---- CGameTask.h : derive signatures from the typedefs
p = SRC + r"\CGameTask.h"
s = open(p, encoding="utf-8").read()
assert "callOriginalVt1C" not in s
slots = re.findall(r"typedef std::function<int\(T\* This((?:, int a\d)*)\)> t_vt([0-9A-F]+);", s)
assert len(slots) == 12, slots
funcs = "\n\t\t// Call the unhooked implementation directly (PX `super` inside overrides).\n"
binds = ""
for i, (params, n) in enumerate(slots):
    names = re.findall(r"a\d", params)
    ptypes = "".join(",int" for _ in names)
    funcs += "\t\tstatic int callOriginalVt%s(T * This%s) {\n" % (n, params)
    funcs += "\t\t\tusing vPtr = std::add_pointer_t<int __fastcall(T*,int%s)>;\n" % ptypes
    funcs += "\t\t\treturn ((vPtr)vtable_original[%d])(This, 0%s);\n\t\t}\n" % (i, "".join(", " + a for a in names))
    binds += '\tlua->set_function(#classname "_CallOriginal_vtable%s", &CGameTask_vtableHooks<classname>::callOriginalVt%s); \\\n' % (n, n)
anchor = "\t\tstatic void registerCallbackVt48(t_vt48 cb) {vtable48_callbacks.push_back(cb);}\n"
assert anchor in s
s = s.replace(anchor, anchor + funcs)
cast = '\tlua->set_function(#classname "_CastCGameTask", &castCGameTask<classname>);'
assert cast in s
s = s.replace(cast, binds + cast)
open(p, "w", encoding="utf-8", newline="").write(s)
print("ok", [n for _, n in slots])
