"""
analyze_clean.py

From run*.csv (bench_clean.py): per-solution time ratio t/t_baseline (geometric
mean over runs); per model median and range over the 10 generations; between-
model tests with the generation as unit (Kruskal-Wallis; pairwise Mann-Whitney,
Holm, Cliff's delta); position of the Human solution within each model's range.
Outputs: ratios.csv, summary.csv, tests.csv, table_runtime.md
"""
import csv, glob, itertools, math, statistics
from scipy.stats import kruskal, mannwhitneyu

MODELS = [("gpt-4o", "GPT-4o"), ("gpt-5.4", "GPT-5.4"), ("gpt-6-astra", "GPT-6 Astra")]
SC = ["P2 documents", "P2 discounts", "P4 discounts"]
acc = {}
for f in sorted(glob.glob("run*.csv")):
    rows = list(csv.DictReader(open(f)))
    base = {r["scenario"]: float(r["median_ns"]) for r in rows if r["variant"] == "Baseline"}
    for r in rows:
        acc.setdefault((r["scenario"], r["variant"]), []).append(float(r["median_ns"]) / base[r["scenario"]])
R = {k: math.exp(statistics.mean(map(math.log, v))) for k, v in acc.items()}
with open("ratios.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["scenario", "variant", "time_ratio"])
    for (s, v), x in sorted(R.items()):
        w.writerow([s, v, round(x, 3)])


def cliff(a, b):
    return (sum(x > y for x in a for y in b) - sum(x < y for x in a for y in b)) / (len(a) * len(b))


def holm(ps):
    o, adj, run = sorted(range(len(ps)), key=lambda i: ps[i]), [0] * len(ps), 0
    for k, i in enumerate(o):
        run = max(run, min(1, (len(ps) - k) * ps[i])); adj[i] = run
    return adj


summary, tests = [], []
for s in SC:
    data = {m: sorted(x for (sc, v), x in R.items() if sc == s and v.startswith(m + " ")) for m, _ in MODELS}
    h = R[(s, "Human")]
    for m, lab in MODELS:
        xs = data[m]
        summary.append({"scenario": s, "solution": lab, "n": len(xs), "median": round(statistics.median(xs), 2),
                        "min": round(xs[0], 2), "max": round(xs[-1], 2), "samples_faster_than_human": sum(x < h for x in xs)})
    summary.append({"scenario": s, "solution": "Human", "n": 1, "median": round(h, 2), "min": "", "max": "", "samples_faster_than_human": ""})
    H, p = kruskal(*data.values())
    tests.append({"scenario": s, "comparison": "Kruskal-Wallis (3 models)", "p_holm": f"{p:.2g}", "cliffs_delta": "", "H": round(H, 2)})
    pairs = list(itertools.combinations([m for m, _ in MODELS], 2))
    ps = [mannwhitneyu(data[a], data[b], alternative="two-sided").pvalue for a, b in pairs]
    for (a, b), pa in zip(pairs, holm(ps)):
        tests.append({"scenario": s, "comparison": f"{a} vs {b}", "p_holm": f"{pa:.2g}", "cliffs_delta": round(cliff(data[a], data[b]), 2), "H": ""})
for fn, d in [("summary.csv", summary), ("tests.csv", tests)]:
    with open(fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(d[0])); w.writeheader(); w.writerows(d)

S = {(r["scenario"], r["solution"]): r for r in summary}
T = {(t["scenario"], t["comparison"]): t for t in tests}
L = ["| Solution | P2 Factory (documents) | P2 Factory (discounts) | P4 Strategy (discounts) |", "|---|---|---|---|",
     "| Baseline | 1.00× | 1.00× | 1.00× |",
     "| Human expert | " + " | ".join(f"{S[(s, 'Human')]['median']:.2f}×" for s in SC) + " |"]
for m, lab in MODELS:
    L.append(f"| {lab} | " + " | ".join(f"{S[(s, lab)]['median']:.2f}× [{S[(s, lab)]['min']:.2f}–{S[(s, lab)]['max']:.2f}]" for s in SC) + " |")
L.append("| Kruskal–Wallis *p* | " + " | ".join(T[(s, "Kruskal-Wallis (3 models)")]["p_holm"] for s in SC) + " |")
L += ["", "Execution time relative to the baseline (lower is better). Models: median [min–max] over 10 independent "
      "generations (GPT-6 Astra in P4: 6 generations; the other 4 changed the interface to Decimal and are not drop-in "
      "replacements). Human expert: single solution."]
open("table_runtime.md", "w").write("\n".join(L) + "\n")
print("\n".join(L)); print()
for t in tests:
    print(t)
for r in summary:
    if r["solution"] != "Human":
        print(r["scenario"], r["solution"], "samples faster than human:", r["samples_faster_than_human"], "/", r["n"])
