"""
reproduce.py -- runs the whole analysis on the generations in llm_samples/.
(Generating new samples requires an API key: see generate_samples.py.)
  python reproduce.py            # ~5 min on a laptop
"""
import subprocess, sys

STEPS = [
    ["static_clean.py", "llm_samples"],
    ["bench_clean.py", "llm_samples", "2026", "run1.csv"],
    ["bench_clean.py", "llm_samples", "2027", "run2.csv"],
    ["analyze_clean.py"],
    ["fig_runtime.py"],
    ["sample_ablations.py", "llm_samples"],
    ["edge_cases.py", "llm_samples"],
]
for step in STEPS:
    print(f"\n>>> python {' '.join(step)}", flush=True)
    subprocess.run([sys.executable, *step], check=True)
print("\nDone: table_static.md, table_runtime.md, fig_runtime.pdf, tests.csv, "
      "sample_ablations.csv, edge_cases_summary.csv")
