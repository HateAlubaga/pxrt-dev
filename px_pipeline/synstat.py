"""Count syntax features over all package pxc + libs; print one example location each."""
import glob, re, os
PK = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
HERE = os.path.dirname(os.path.abspath(__file__))
files = glob.glob(PK + r"\*\0.0.1\scripts_px\*.pxc") + glob.glob(HERE + r"\pxl\*.pxc")
PAT = {
    "switch": r"\bswitch\s*\(", "case": r"\bcase\b", "do": r"\bdo\s*\{", "while": r"\bwhile\s*\(",
    "goto": r"\bgoto\b", "struct": r"\bstruct\b", "enum_decl": r"\benum\s+\w+\s*\{", "class_decl": r"\bclass\s+\w+",
    "ternary": r"\?[^:;]*:", "is_op": r"\bis\s+C\w+", "addr_of": r"[(,=]\s*&\w", "pow_caret": r"\w\s*\^\s*[\w(]",
    "incdec_pre": r"(\+\+|--)\w", "incdec_post": r"\w(\+\+|--)", "deref_dot": r"\w\.\w", "arrow": r"->",
    "array_decl": r"\b\w+\s+\w+\[\d+\]\s*;", "new": r"\bnew\s+\w+", "delete": r"\bdelete\b", "cast_ptr": r"\(\s*C\w+\s*\*\s*\)",
    "local_in_if": r"\b(if\s*\(.*\)|else)\s*local\b", "string_lit": r'"', "char_lit": r"'.'", "hex": r"0x[0-9a-fA-F]+",
    "label": r"(?m)^\s*\w+:\s*$", "static": r"\bstatic\b", "const": r"\bconst\b", "unsigned": r"\bunsigned\b",
    "sizeof": r"\bsizeof\b", "typedef": r"\btypedef\b", "define": r"#\w+", "float_f": r"\d\.\d+f\b",
    "compound_bit": r"(\|=|&=|\^=|<<=|>>=)", "shift": r"(<<|>>)", "comma_for": r"for\s*\([^;]*,[^;]*;",
    "block_comment": r"/\*", "method_decl": r"(?m)^\s*(\w+\s*\*?\s+)?\w+::\w+\s*\(", "override": r"\boverride\b",
    "funcptr": r"\bfunction\b", "this_arrow": r"\bthis\s*->", "super_call": r"\bsuper\s*\(", "super_dot": r"\bsuper\s*[.-]",
    "return_super": r"return\s+super", "eq_super": r"=\s*super\s*;",
}
cnt = {k: 0 for k in PAT}
ex = {}
for fn in files:
    t = open(fn, encoding="latin-1").read()
    t2 = re.sub(r"//[^\n]*", "", t)
    for k, p in PAT.items():
        ms = list(re.finditer(p, t2))
        if ms:
            cnt[k] += len(ms)
            if k not in ex:
                m = ms[0]
                ln = t2.count("\n", 0, m.start()) + 1
                line = t2.splitlines()[ln - 1].strip()[:90]
                ex[k] = "%s:%d  %s" % (os.path.basename(fn), ln, line)
for k in PAT:
    print("%-14s %6d  %s" % (k, cnt[k], ex.get(k, "")))
print("files", len(files))
