"""Symbol tables for PX packages: per-package declarations incl. required libs."""
import json, os
from pxast import parse, PXError

HERE = os.path.dirname(os.path.abspath(__file__))
_CORPUS = None
_PARSED = {}


def corpus():
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))
    return _CORPUS


def parsed(key):
    if key not in _PARSED:
        _PARSED[key] = parse(corpus()[key], key)
    return _PARSED[key]


def packages():
    out = {}
    for k in corpus():
        if k.startswith("@lib/"):
            continue
        out.setdefault(k.split("/")[0], []).append(k)
    return out


def lib_files(name):
    """Files providing library `name` (require name)."""
    C = corpus()
    k = "@lib/%s.pxc" % name
    if k in C:
        return [k]
    pk = [x for x in C if x.split("/")[0] == name and not x.startswith("@lib/")]
    return sorted(pk)


class Decls:
    def __init__(self):
        self.funcs = {}       # free function name -> func dict
        self.methods = {}     # (cls, name) -> [func dict]
        self.ctors = {}       # cls -> [func dict]
        self.gvars = {}       # name -> type
        self.enums = {}       # enum type -> [members]
        self.enum_members = {}  # member -> enum type
        self.classes = {}     # name -> base
        self.flags = set()
        self.requires = []
        self.entries = {}     # (script, name) -> func

    def cls_chain(self, cls):
        seen = []
        while cls and cls not in seen:
            seen.append(cls)
            cls = self.classes.get(cls)
        return seen

    def has_method(self, cls, name):
        return any((c, name) in self.methods for c in self.cls_chain(cls))


ENTRY_NAMES = {"InitGraphic", "FirstFrame", "Init", "InitSMap"}


def script_classes(ast, script):
    """Script (entry-holder) class names in one file: the basename plus any
    class owning entry-named funcs that has no ctor/classdecl in the file
    (lib files hold many `//==== script X ====` sections)."""
    real = set()
    for node in ast:
        if node[0] == "classdecl":
            real.add(node[1])
        elif node[0] == "func" and node[1]["cls"] and node[1]["cls"] == node[1]["name"]:
            real.add(node[1]["cls"])
    out = {script}
    for node in ast:
        if node[0] == "func":
            f = node[1]
            if f["cls"] and f["name"] in ENTRY_NAMES and not f["override"] and f["cls"] not in real:
                out.add(f["cls"])
    return out


def collect(files, d=None, script_names=None):
    d = d or Decls()
    for k in files:
        ast = parsed(k)
        script = os.path.splitext(os.path.basename(k))[0]
        scls = script_classes(ast, script)
        if script_names is not None:
            script_names.update(scls)
        for node in ast:
            kind = node[0]
            if kind == "require":
                d.requires.extend(node[1])
            elif kind == "flag":
                d.flags.add(node[1])
            elif kind == "enum":
                d.enums[node[1]] = [m for m, _ in node[2]]
                for m, _ in node[2]:
                    d.enum_members[m] = node[1]
            elif kind == "classdecl":
                d.classes[node[1]] = node[2]
            elif kind == "gdecl":
                for (name, dims, init, extra) in node[2]:
                    d.gvars[name] = (node[1][0], node[1][1] + extra, len(dims))
            elif kind == "func":
                f = node[1]
                f["file"] = k
                if f["cls"] is None:
                    d.funcs.setdefault(f["name"], f)
                elif f["cls"] == f["name"]:
                    d.ctors.setdefault(f["cls"], []).append(f)
                elif f["cls"] in scls and not f["override"]:
                    d.entries[(f["cls"], f["name"])] = f
                else:
                    d.methods.setdefault((f["cls"], f["name"]), []).append(f)
    return d


def package_decls(pkg_files, visited=None):
    """Declarations visible in a package: own files + required libs (transitive)."""
    visited = visited if visited is not None else set()
    own = collect(pkg_files)
    full = Decls()
    libs = []

    def add_lib(name):
        if name in visited:
            return
        visited.add(name)
        fl = lib_files(name)
        if not fl:
            return
        sub = collect(fl)
        for r in sub.requires:
            add_lib(r)
        libs.append((name, fl))

    for r in own.requires:
        add_lib(r)
    for name, fl in libs:
        collect(fl, full)
    collect(pkg_files, full)
    full.requires = own.requires
    return own, full, libs
