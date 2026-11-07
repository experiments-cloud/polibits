"""
static_clean.py -> static.csv, table_static.md

Radon 6.0.1 on production code only (comments, docstrings, __main__ demo and
top-level self-test functions removed). CC = max over functions and methods.
P4 is compared with the baseline restricted to the discount logic.
"""
import ast, csv, pathlib, re, statistics, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from metrics_common import normalize, metrics

SELFTEST = re.compile(r"^(main|verify|test|run_|check|demo)", re.I)


def prod(code, ex):
    t = ast.parse(code)
    t.body = [n for n in t.body if not (isinstance(n, ast.FunctionDef) and SELFTEST.match(n.name))]
    if ex == "P4":
        for n in ast.walk(t):
            if isinstance(n, ast.ClassDef):
                n.body = [m for m in n.body if not (isinstance(m, ast.FunctionDef) and m.name == "execute_document_process")] or [ast.Pass()]
    return ast.unparse(t)


root = pathlib.Path(sys.argv[1])
rows = []
here = pathlib.Path(__file__).parent
rows.append({"exercise": "P2", "solution": "Baseline", "sample": "", **metrics(normalize((here / "p1_control.py").read_text()))})
rows.append({"exercise": "P4", "solution": "Baseline", "sample": "", **metrics(normalize((here / "p1_control.py").read_text(), drop_method="execute_document_process"))})
rows.append({"exercise": "P2", "solution": "Human", "sample": "", **metrics(normalize((here / "p2_creational_h.py").read_text()))})
rows.append({"exercise": "P4", "solution": "Human", "sample": "", **metrics(normalize((here / "p4_behavioral_h.py").read_text()))})
for p in sorted(root.glob("code/P*/*/sample_*.py")):
    ex = p.parts[-3]
    rows.append({"exercise": ex, "solution": p.parts[-2], "sample": p.stem, **metrics(prod(normalize(p.read_text(encoding="utf-8")), ex))})
with open("static.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

L = ["| Solution | CC (P2) | MI (P2) | SLOC (P2) | CC (P4) | MI (P4) | SLOC (P4) |", "|---|---|---|---|---|---|---|"]
for sol, lab in [("Baseline", "Baseline"), ("Human", "Human expert"), ("gpt-4o", "GPT-4o"), ("gpt-5.4", "GPT-5.4"), ("gpt-6-astra", "GPT-6 Astra")]:
    cells = []
    for ex in ["P2", "P4"]:
        R = [r for r in rows if r["exercise"] == ex and r["solution"] == sol]
        if len(R) == 1:
            cells += [str(R[0]["cc_max_method"]), f"{R[0]['mi']:.1f}", str(R[0]["sloc"])]
        else:
            cc = sorted(r["cc_max_method"] for r in R); mi = sorted(r["mi"] for r in R); sl = sorted(r["sloc"] for r in R)
            cells += [f"{statistics.median(cc):g} [{cc[0]}–{cc[-1]}]", f"{statistics.median(mi):.1f} [{mi[0]:.1f}–{mi[-1]:.1f}]",
                      f"{statistics.median(sl):g} [{sl[0]}–{sl[-1]}]"]
    L.append(f"| {lab} | " + " | ".join(cells) + " |")
L += ["", "CC: maximum cyclomatic complexity over functions and methods. MI: Radon Maintainability Index (0–100) "
      "on code without comments. Models: median [min–max] over 10 generations. P4 baseline: discount logic only."]
open("table_static.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
