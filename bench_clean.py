"""
bench_clean.py

Runtime benchmark for the study design only:
  Baseline, Human (as delivered), and 10 independent generations of each model
  (gpt-4o, gpt-5.4, gpt-6-astra) produced by generate_samples.py.
Protocol: functional-equivalence check on the benchmark inputs, then 20,000
iterations x 30 rounds in randomized order; statistic = median ns per call.
Samples whose public API requires decimal.Decimal are not drop-in replacements
of the float-based baseline; they are listed apart and not timed.
Usage: python bench_clean.py SAMPLES_ROOT SEED OUT.csv
"""
import csv, pathlib, random, statistics, sys, timeit
import p1_control, p2_creational_h, p4_behavioral_h
from adapters import load, p2_entry, p4_entry

ITERATIONS, N_ROUNDS = 20_000, 30
DATA = "Data" * 50
DOC = [(f, DATA) for f in ["pdf", "json", "xml", "csv"]]
DISC = [("REGULAR", 500.0, 12), ("VIP", 1200.0, 5), ("VIP", 500.0, 5), ("STUDENT", 300.0, 2)]
base = p1_control.MonolithicSystem()


def collect(root):
    h2, h4 = p2_creational_h.CreationalSystem(), p4_behavioral_h.BehavioralSystem()
    def human_p4(t, p, i):
        h4.set_strategy_by_name(t)
        return h4.process_sale(p, i)
    G = {"P2 documents": ({"Baseline": base.execute_document_process, "Human": h2.execute_document_process}, DOC),
         "P2 discounts": ({"Baseline": base.execute_ecommerce_discounts, "Human": h2.execute_ecommerce_discounts}, DISC),
         "P4 discounts": ({"Baseline": base.execute_ecommerce_discounts, "Human": human_p4}, DISC)}
    excluded = []
    for path in sorted(pathlib.Path(root).glob("code/P*/*/sample_*.py")):
        ex, model, s = path.parts[-3], path.parts[-2], path.stem
        mod = load(path, f"{ex}_{model}_{s}".replace("-", "_").replace(".", "_"))
        label = f"{model} {s[-2:]}"
        if ex == "P2":
            d, c = p2_entry(mod)
            G["P2 documents"][0][label] = d
            G["P2 discounts"][0][label] = c
        else:
            fn = p4_entry(mod)
            try:
                ok = all(fn(*k) == base.execute_ecommerce_discounts(*k) for k in DISC)
            except TypeError:
                ok = False
            if ok:
                G["P4 discounts"][0][label] = fn
            else:
                excluded.append(label)
    return G, excluded


def main():
    root, seed, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    rng = random.Random(seed)
    G, excluded = collect(root)
    print("P4 samples not drop-in (Decimal API), not timed:", excluded)
    rows = []
    for title, (variants, cases) in G.items():
        ref = variants["Baseline"]
        for n, fn in variants.items():
            for k in cases:
                assert fn(*k) == ref(*k), (title, n, k)
        def wl(fn):
            def w():
                for k in cases:
                    fn(*k)
            return w
        work = {n: wl(f) for n, f in variants.items()}
        for w in work.values():
            for _ in range(500):
                w()
        smp = {n: [] for n in work}
        names = list(work)
        for _ in range(N_ROUNDS):
            rng.shuffle(names)
            for n in names:
                smp[n].append(timeit.Timer(work[n]).timeit(number=ITERATIONS) / (ITERATIONS * len(cases)) * 1e9)
        for n, s in smp.items():
            rows.append({"scenario": title, "variant": n, "median_ns": round(statistics.median(s), 1)})
        print(f"done {title}: {len(variants)} variants", flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
