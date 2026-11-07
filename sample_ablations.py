"""
sample_ablations.py

Per-sample ablations on the new samples, to test causally the two decisions
that the association analysis pointed to. Each ablation removes ONE decision
and keeps everything else; the ablated solution must still return the baseline
output.

  A1 (GPT-5.4, P4, samples with a frozen dataclass built per request):
      @dataclass(frozen=True) -> @dataclass(frozen=False) (AST edit). In addition,
      the cost of constructing the frozen dataclass alone is timed, to estimate the
      share of the overhead spent creating the parameter object.
  A2 (GPT-4o, P2, samples that rebuild the lookup dict per request):
      the dict literal is hoisted (AST transformation) to a module-level constant.

Share of overhead removed = (t_orig - t_abl) / (t_orig - t_base).
Output: sample_ablations.csv
"""
import ast, csv, dataclasses, pathlib, random, statistics, sys, timeit, types
import p1_control
from adapters import load, p2_entry, p4_entry

ROOT = pathlib.Path(sys.argv[1])
ITER, ROUNDS = 20_000, 30
DATA = "Data" * 50
DOC = [(f, DATA) for f in ["pdf", "json", "xml", "csv"]]
DISC = [("REGULAR", 500.0, 12), ("VIP", 1200.0, 5), ("VIP", 500.0, 5), ("STUDENT", 300.0, 2)]
base = p1_control.MonolithicSystem()


class Unfreeze(ast.NodeTransformer):
    """@dataclass(frozen=True) -> @dataclass(frozen=False); nothing else changes."""
    def __init__(self):
        self.n = 0
    def visit_ClassDef(self, node):
        for d in node.decorator_list:
            if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "dataclass":
                for k in d.keywords:
                    if k.arg == "frozen" and getattr(k.value, "value", False) is True:
                        k.value = ast.Constant(False); self.n += 1
        return node


def exec_tree(tree, path, name):
    ast.fix_missing_locations(tree)
    mod = types.ModuleType(name); sys.modules[name] = mod
    exec(compile(tree, str(path) + " [ablated]", "exec"), mod.__dict__)
    return mod


def a1(path, tag):
    """A1: frozen dataclass -> plain (mutable) dataclass. Also returns the per-request
    construction cost of the frozen dataclass, timed alone with the benchmark inputs."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    u = Unfreeze(); tree = u.visit(tree)
    if not u.n:
        return None
    mod = exec_tree(tree, path, tag + "_abl")
    orig = load(path, tag + "_orig2")
    frozen = [c for c in vars(orig).values() if isinstance(c, type) and dataclasses.is_dataclass(c)
              and c.__dataclass_params__.frozen and c.__module__ == orig.__name__]
    cls = frozen[0]
    f0, f1 = [f.name for f in dataclasses.fields(cls)][:2]
    ns = {"cls": cls, "DISC": DISC}
    # same call form as in the samples: cls(price=price, items_count=items_count)
    exec(f"def construct_only():\n    for _, p, i in DISC:\n        cls({f0}=p, {f1}=i)\n"
         f"def empty_loop():\n    for _, p, i in DISC:\n        pass\n", ns)
    t = lambda f: statistics.median(timeit.repeat(f, number=ITER, repeat=15)) / (ITER * len(DISC)) * 1e9
    t_dc = t(ns["construct_only"]) - t(ns["empty_loop"])
    return p4_entry(mod), t_dc


class Hoist(ast.NodeTransformer):
    """Move `name = {...}` (>=3 keys) out of non-__init__ methods to module constants."""
    def __init__(self):
        self.hoisted = []
    def visit_FunctionDef(self, node):
        if node.name != "__init__":
            for i, st in enumerate(node.body):
                if isinstance(st, (ast.Assign, ast.AnnAssign)) and isinstance(st.value, ast.Dict) and len(st.value.keys) >= 3:
                    const = f"_HOISTED_{len(self.hoisted)}"
                    self.hoisted.append(ast.Assign(targets=[ast.Name(const, ast.Store())], value=st.value))
                    st.value = ast.Name(const, ast.Load())
        return node


def a2(path, tag):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    h = Hoist(); tree = h.visit(tree)
    if not h.hoisted:
        return None
    main = [n for n in tree.body if isinstance(n, ast.If) and getattr(getattr(n.test, "left", None), "id", "") == "__name__"]
    tree.body = [n for n in tree.body if n not in main] + h.hoisted
    ast.fix_missing_locations(tree)
    mod = types.ModuleType(tag + "_abl"); sys.modules[mod.__name__] = mod
    exec(compile(tree, str(path) + " [hoisted]", "exec"), mod.__dict__)
    return p2_entry(mod)


def timed(variants, cases, rng):
    def wl(fn):
        def w():
            for c in cases:
                fn(*c)
        return w
    work = {n: wl(f) for n, f in variants.items()}
    for w in work.values():
        for _ in range(500):
            w()
    s = {n: [] for n in work}
    names = list(work)
    for _ in range(ROUNDS):
        rng.shuffle(names)
        for n in names:
            s[n].append(timeit.Timer(work[n]).timeit(number=ITER) / (ITER * len(cases)) * 1e9)
    return {n: statistics.median(v) for n, v in s.items()}


def main():
    rng = random.Random(2026)
    rows = []
    jobs = []
    dc_cost = {}
    for path in sorted(ROOT.glob("code/P4/gpt-5.4/sample_*.py")):
        tag = f"A1_{path.stem}"
        r = a1(path, tag)
        if r:
            dc_cost[path.stem] = r[1]
            jobs.append(("A1 frozen->mutable dataclass", "P4 discounts", path.stem, p4_entry(load(path, tag)), r[0], DISC, base.execute_ecommerce_discounts))
    for path in sorted(ROOT.glob("code/P2/gpt-4o/sample_*.py")):
        tag = f"A2_{path.stem}"
        r = a2(path, tag)
        if r:
            od, oc = p2_entry(load(path, tag))
            jobs.append(("A2 dict per call", "P2 documents", path.stem, od, r[0], DOC, base.execute_document_process))
            jobs.append(("A2 dict per call", "P2 discounts", path.stem, oc, r[1], DISC, base.execute_ecommerce_discounts))
    for abl, scen, s, orig, ablated, cases, ref in jobs:
        for c in cases:
            assert ablated(*c) == ref(*c) == orig(*c), (abl, s, c)
        t = timed({"base": ref, "orig": orig, "abl": ablated}, cases, rng)
        share = (t["orig"] - t["abl"]) / (t["orig"] - t["base"]) * 100
        rows.append({"ablation": abl, "scenario": scen, "sample": s, "base_ns": round(t["base"], 1),
                     "orig_ns": round(t["orig"], 1), "ablated_ns": round(t["abl"], 1),
                     "orig_ratio": round(t["orig"] / t["base"], 2), "ablated_ratio": round(t["abl"] / t["base"], 2),
                     "share_of_overhead_removed_pct": round(share, 1),
                     "dataclass_construction_share_pct": round(dc_cost[s] / (t["orig"] - t["base"]) * 100, 1) if abl.startswith("A1") else ""})
        print(rows[-1], flush=True)
    with open("sample_ablations.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for abl in sorted({r["ablation"] + " | " + r["scenario"] for r in rows}):
        sh = [r["share_of_overhead_removed_pct"] for r in rows if r["ablation"] + " | " + r["scenario"] == abl]
        print(f"{abl}: n={len(sh)} median share removed {statistics.median(sh):.0f}% (range {min(sh):.0f}-{max(sh):.0f}%)")
    dcs = [r["dataclass_construction_share_pct"] for r in rows if r["ablation"].startswith("A1")]
    if dcs:
        print(f"Frozen dataclass construction alone = median {statistics.median(dcs):.0f}% of the overhead (range {min(dcs):.0f}-{max(dcs):.0f}%)")


if __name__ == "__main__":
    main()
