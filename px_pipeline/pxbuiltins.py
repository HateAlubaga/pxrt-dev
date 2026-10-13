"""Census of undeclared names over the whole corpus -> px/builtins_census.json + report."""
import json, os, collections, re
from pxsym import packages, package_decls, parsed, lib_files, corpus

HERE = os.path.dirname(os.path.abspath(__file__))


def func_locals(f):
    names = set(p[1] for p in f["params"] if p[1])

    def walk(s):
        if s is None:
            return
        k = s[0]
        if k == "block":
            for x in s[1]:
                walk(x)
        elif k == "if":
            walk(s[2]); walk(s[3])
        elif k == "while":
            walk(s[2])
        elif k == "for":
            walk(s[1]); walk(s[4])
        elif k == "decl":
            for (n, dims, init, extra) in s[2]:
                names.add(n)
        elif k == "local":
            for (n, init) in s[1]:
                names.add(n)
    walk(f["body"])
    return names


def exprs_of_stmt(s, out):
    if s is None:
        return
    k = s[0]
    if k == "block":
        for x in s[1]:
            exprs_of_stmt(x, out)
    elif k == "if":
        out.append(s[1]); exprs_of_stmt(s[2], out); exprs_of_stmt(s[3], out)
    elif k == "while":
        out.append(s[1]); exprs_of_stmt(s[2], out)
    elif k == "for":
        exprs_of_stmt(s[1], out)
        if s[2] is not None: out.append(s[2])
        if s[3] is not None: out.append(s[3])
        exprs_of_stmt(s[4], out)
    elif k == "ret":
        if s[1] is not None: out.append(s[1])
    elif k == "decl":
        for (n, dims, init, extra) in s[2]:
            out.extend(dims)
            if init is not None: out.append(init)
    elif k == "local":
        for (n, init) in s[1]:
            if init is not None: out.append(init)
    elif k == "expr":
        out.append(s[1])
    elif k == "delete":
        out.append(s[1])


def walk_expr(e, cb, ctx="r"):
    """cb(kind, node, ctx) kinds: name, call, mem, mcall"""
    k = e[0]
    if k == "name":
        cb("name", e, ctx)
    elif k == "call":
        fn = e[1]
        if fn[0] == "name":
            cb("call", fn, len(e[2]))
        elif fn[0] == "mem":
            cb("mcall", fn, len(e[2]))
            walk_expr(fn[1], cb)
        elif fn[0] == "super":
            pass
        else:
            walk_expr(fn, cb)
        for a in e[2]:
            walk_expr(a, cb)
    elif k == "idx":
        walk_expr(e[1], cb, ctx); walk_expr(e[2], cb)
    elif k == "mem":
        cb("mem", e, ctx)
        walk_expr(e[1], cb)
    elif k == "un":
        walk_expr(e[2], cb, "a" if e[1] == "&" else "r")
    elif k == "bin":
        walk_expr(e[2], cb); walk_expr(e[3], cb)
    elif k == "asg":
        walk_expr(e[2], cb, "w"); walk_expr(e[3], cb)
    elif k in ("post", "pre"):
        walk_expr(e[2], cb, "w")
    elif k == "new":
        for a in (e[2] or []):
            walk_expr(a, cb)
        if e[3] is not None:
            walk_expr(e[3], cb)
    elif k == "is":
        walk_expr(e[1], cb)


def main():
    P = packages()
    call_free = collections.Counter()      # undeclared bare calls in free/entry funcs
    call_meth = collections.defaultdict(collections.Counter)  # cls -> name
    name_free_r = collections.Counter()
    name_free_w = collections.Counter()
    name_meth_r = collections.defaultdict(collections.Counter)
    name_meth_w = collections.defaultdict(collections.Counter)
    members = collections.Counter()
    mcalls = collections.Counter()
    arity = collections.defaultdict(set)
    where = collections.defaultdict(set)
    done_libs = set()
    units = [(pkg, files) for pkg, files in P.items()]
    for lib in [k[5:-4] for k in corpus() if k.startswith("@lib/")]:
        units.append(("@" + lib, ["@lib/%s.pxc" % lib]))
    for pkg, files in units:
        try:
            own, full, libs = package_decls(files)
        except Exception as ex:
            print("ERR", pkg, ex)
            continue
        for k in files:
            for node in parsed(k):
                if node[0] != "func" or node[1]["body"] is None:
                    continue
                f = node[1]
                script = os.path.splitext(os.path.basename(k))[0]
                is_method = f["cls"] is not None and f["cls"] != script
                cls = f["cls"]
                loc = func_locals(f)
                ex = []
                exprs_of_stmt(f["body"], ex)

                def cb(kind, n, ctx):
                    if kind == "name":
                        nm = n[1]
                        if nm in loc or nm in full.gvars or nm in full.enum_members or nm in full.funcs:
                            return
                        if is_method:
                            (name_meth_w if ctx == "w" else name_meth_r)[cls][nm] += 1
                        else:
                            (name_free_w if ctx == "w" else name_free_r)[nm] += 1
                        where[nm].add(pkg)
                    elif kind == "call":
                        nm = n[1]
                        if nm in full.funcs or nm in loc or nm in full.classes or nm in full.gvars:
                            return
                        if is_method and full.has_method(cls, nm):
                            return
                        arity[nm].add(ctx)
                        where[nm].add(pkg)
                        if is_method:
                            call_meth[cls][nm] += 1
                        else:
                            call_free[nm] += 1
                    elif kind == "mem":
                        members[n[2]] += 1
                    elif kind == "mcall":
                        mcalls[n[2]] += 1
                for e in ex:
                    walk_expr(e, cb)
    allmeth = collections.Counter()
    for c, cnt in call_meth.items():
        allmeth.update(cnt)
    res = dict(
        call_free=call_free.most_common(),
        call_meth={c: v.most_common() for c, v in call_meth.items()},
        call_meth_all=allmeth.most_common(),
        name_free_r=name_free_r.most_common(), name_free_w=name_free_w.most_common(),
        name_meth_r={c: v.most_common() for c, v in name_meth_r.items()},
        name_meth_w={c: v.most_common() for c, v in name_meth_w.items()},
        members=members.most_common(), mcalls=mcalls.most_common(),
        arity={k: sorted(v) for k, v in arity.items()},
        npkgs={k: len(v) for k, v in where.items()},
    )
    os.makedirs(os.path.join(HERE, "px"), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, "px", "census.json"), "w"), indent=0)
    with open(os.path.join(HERE, "census.txt"), "w", encoding="utf-8") as fo:
        fo.write("== bare calls in free/entry funcs (undeclared): %d\n" % len(call_free))
        fo.write(" ".join("%s:%d" % x for x in call_free.most_common()) + "\n")
        fo.write("== bare calls in methods, not free-declared, not package method: %d\n" % len(allmeth))
        fo.write(" ".join("%s:%d" % x for x in allmeth.most_common()) + "\n")
        fo.write("== method-only calls (never in free funcs)\n")
        fo.write(" ".join("%s:%d" % x for x in allmeth.most_common() if x[0] not in call_free) + "\n")
        fo.write("== names read in free funcs\n" + " ".join("%s:%d" % x for x in name_free_r.most_common()) + "\n")
        fo.write("== names written in free funcs\n" + " ".join("%s:%d" % x for x in name_free_w.most_common()) + "\n")
        mr = collections.Counter()
        for c, v in name_meth_r.items():
            mr.update(v)
        fo.write("== names read in methods (all cls)\n" + " ".join("%s:%d" % x for x in mr.most_common()) + "\n")
        fo.write("== members\n" + " ".join("%s:%d" % x for x in members.most_common()) + "\n")
        fo.write("== member calls\n" + " ".join("%s:%d" % x for x in mcalls.most_common()) + "\n")
    print("done", len(call_free), len(allmeth), len(members), len(mcalls))


if __name__ == "__main__":
    main()
