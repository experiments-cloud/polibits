# Replication package: structural quality vs. runtime cost of LLM-generated design-pattern refactorings (Python)

## Contents

| File | Role |
|---|---|
| `p1_control.py` | Baseline: coupled system with `if-elif` chains. |
| `p2_creational_h.py`, `p4_behavioral_h.py` | Human expert's solutions (P2: Factory Method; P4: Strategy). |
| `reproducibility_exp_1.py`, `reproducibility_exp_2.py` | The exact prompts and API parameters for P2 and P4. |
| `generate_samples.py` | Generates N independent solutions per model and exercise with those prompts. It saves the raw API responses, extracts the code automatically and writes a manifest. |
| `llm_samples.zip` | The generations used in the paper: 10 per model and exercise for `gpt-4o`, `gpt-5.4` and `gpt-6-astra`. Includes `raw/` (verbatim answers and full API responses), `code/` (extracted code) and `manifest.csv` (returned model snapshot, tokens, extraction). |
| `adapters.py` | One fixed rule that connects every generation to the benchmark (see its docstring). |
| `metrics_common.py`, `static_clean.py` | Radon 6.0.1 metrics on production code: CC (maximum over functions and methods), MI and SLOC. Writes `static.csv` and `table_static.md`. |
| `bench_clean.py` | Checks functional equivalence on the benchmark inputs, then times each solution: 20,000 iterations × 30 rounds in randomized order; the reported statistic is the median ns per call. |
| `analyze_clean.py` | Computes time relative to the baseline and compares the models with each generation as the unit of analysis (Kruskal–Wallis; pairwise Mann–Whitney with Holm correction; Cliff's delta). Writes `ratios.csv`, `summary.csv`, `tests.csv` and `table_runtime.md`. |
| `sample_ablations.py` | Removes one design decision at a time from the generations that contain it, and measures how much overhead disappears. Writes `sample_ablations.csv`. |
| `edge_cases.py` | Checks behaviour on 16 inputs outside the benchmark. Writes `edge_cases.csv` and `edge_cases_summary.csv`. |
| `reproduce.py` | Runs the whole analysis. |

## Reproduce

```
pip install -r requirements.txt
python reproduce.py
```

Requires Python 3.12. Absolute times depend on the machine; the ratios relative to the baseline and the ranking of the solutions are what the paper reports.

## Generating new samples (optional, requires an OpenAI API key)

```
export OPENAI_API_KEY=...        # Windows: set OPENAI_API_KEY=...
python generate_samples.py --dry-run
python generate_samples.py --n 10
```

## License

MIT (see `LICENSE`).
