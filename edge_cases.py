"""
edge_cases.py

Behaviour on inputs outside the benchmark, compared with the baseline:
letter case, padding, unknown keys, boundaries and negative values.
A solution matches a case when its outcome (return value, or exception type)
equals the baseline's. Covers the Human solution and every generation; the
P4 generations with a Decimal interface receive Decimal prices and are compared
numerically.
Usage: python edge_cases.py SAMPLES_ROOT  ->  edge_cases.csv, edge_cases_summary.csv
"""
import csv, pathlib, sys
from decimal import Decimal
import p1_control
from adapters import load, p4_entry
from bench_clean import collect

DOC = {"lowercase 'pdf'": ("pdf", "x"), "uppercase 'PDF'": ("PDF", "x"), "padded ' pdf '": (" pdf ", "x"),
       "unknown format": ("yaml", "x"), "empty data": ("pdf", "")}
DISC = {"REGULAR 10 items": ("REGULAR", 500.0, 10), "REGULAR 11 items": ("REGULAR", 500.0, 11),
        "VIP price 1000": ("VIP", 1000.0, 1), "VIP price 1000.01": ("VIP", 1000.01, 1),
        "lowercase 'vip'": ("vip", 1200.0, 1), "padded ' VIP '": (" VIP ", 1200.0, 1),
        "unknown type": ("GOLD", 100.0, 1), "BLACK_FRIDAY": ("BLACK_FRIDAY", 100.0, 1),
        "price 0": ("STUDENT", 0.0, 1), "negative price": ("STUDENT", -10.0, 1),
        "negative items": ("REGULAR", 100.0, -1)}
base = p1_control.MonolithicSystem()


def outcome(fn, args, decimal=False):
    if decimal:
        args = tuple(Decimal(str(a)) if isinstance(a, float) else a for a in args)
    try:
        r = fn(*args)
        return float(r) if isinstance(r, Decimal) else r
    except Exception as e:
        return f"<{type(e).__name__}>"


def main():
    root = sys.argv[1]
    G, excluded = collect(root)
    plan = [("P2 documents", DOC, base.execute_document_process),
            ("P2 discounts", DISC, base.execute_ecommerce_discounts),
            ("P4 discounts", DISC, base.execute_ecommerce_discounts)]
    rows = []
    for sc, cases, ref in plan:
        variants = {n: (f, False) for n, f in G[sc][0].items() if n != "Baseline"}
        if sc == "P4 discounts":
            for label in excluded:      # Decimal-interface generations
                model, s = label.split()
                path = pathlib.Path(root) / "code" / "P4" / model / f"sample_{s}.py"
                variants[label] = (p4_entry(load(path, f"edge_{model}_{s}".replace("-", "_").replace(".", "_"))), True)
        for name, (fn, dec) in variants.items():
            for cname, args in cases.items():
                exp, got = outcome(ref, args), outcome(fn, args, dec)
                rows.append({"scenario": sc, "solution": name, "case": cname, "baseline": exp,
                             "solution_output": got, "match": int(exp == got)})
    with open("edge_cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    # summary: generations that match the baseline on every edge case of the exercise
    full = {}
    for r in rows:
        ex = r["scenario"][:2]
        full[(ex, r["solution"])] = full.get((ex, r["solution"]), True) and r["match"] == 1
    summ = []
    for ex in ["P2", "P4"]:
        for sol in ["Human", "gpt-4o", "gpt-5.4", "gpt-6-astra"]:
            ks = [k for k in full if k[0] == ex and (k[1] == sol or k[1].startswith(sol + " "))]
            summ.append({"exercise": ex, "solution": sol, "fully_matching": sum(full[k] for k in ks), "total": len(ks)})
    with open("edge_cases_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
    for s in summ:
        print(s)


if __name__ == "__main__":
    main()
