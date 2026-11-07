"""
generate_samples.py

Generates N independent refactorings per model and exercise with EXACTLY the
same prompts and parameters as reproducibility_exp_1.py (P2, Factory Method)
and reproducibility_exp_2.py (P4, Strategy). The prompts are read from those
two scripts at run time, so they cannot drift.

For every call it saves:
  raw/<exercise>/<model>/sample_XX.json  full API response + request metadata
  raw/<exercise>/<model>/sample_XX.md    the model's answer, verbatim
  code/<exercise>/<model>/sample_XX.py   code extracted automatically (rule below)
and appends one line to manifest.csv.

Code-extraction rule (no manual editing): take every fenced ```python block,
keep the ones that parse with ast, and use the longest one. If there are no
fences, use the whole answer if it parses. If nothing parses, no .py is written
and the manifest records extraction="failed".

The script can be stopped and resumed: samples that already exist are skipped.

Usage (from the folder that contains p1_control.py and the two reproducibility scripts):
  export OPENAI_API_KEY=...            # never hard-code it
  python generate_samples.py --dry-run                 # plan + token estimate, no API calls
  python generate_samples.py --n 10                    # default models, asks for confirmation
  python generate_samples.py --n 10 --models gpt-4o-2024-08-06 gpt-5.4 --yes
"""
import argparse
import ast
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
# gpt-3.5-turbo was shut down by OpenAI on 2026-10-23; it is replaced by the
# current flagship so that the study still spans three generations:
#   gpt-4o (2024, non-reasoning, T=0) -> gpt-5.4 (Mar 2026) -> gpt-6-astra (Sep 2026)
DEFAULT_MODELS = ["gpt-4o", "gpt-5.4", "gpt-6-astra"]
EXERCISES = {"P2": "reproducibility_exp_1.py", "P4": "reproducibility_exp_2.py"}
NO_TEMPERATURE_PREFIXES = ("gpt-5", "gpt-6", "o1", "o3", "o4")   # reasoning models reject temperature
MANIFEST_FIELDS = ["timestamp_utc", "exercise", "model_requested", "model_returned",
                   "system_fingerprint", "sample", "temperature_sent", "prompt_sha256",
                   "prompt_tokens", "completion_tokens", "reasoning_tokens",
                   "finish_reason", "extraction", "code_file", "raw_file", "status"]


# --------------------------------------------------------------------------
# Prompts: read verbatim from the original scripts
# --------------------------------------------------------------------------
def load_prompt(script_name):
    tree = ast.parse((HERE / script_name).read_text(encoding="utf-8"))
    instruction, system = None, None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "prompt_instruccion" for t in node.targets):
            instruction = ast.literal_eval(node.value)
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if keys == ["role", "content"] and isinstance(node.values[0], ast.Constant) \
                    and node.values[0].value == "system":
                system = ast.literal_eval(node.values[1])
    if instruction is None or system is None:
        sys.exit(f"Could not read the prompt from {script_name}")
    base_code = (HERE / "p1_control.py").read_text(encoding="utf-8")
    user = f"{instruction}\n{base_code}"          # identical concatenation to the original
    return system, user


def supports_temperature(model):
    return not model.startswith(NO_TEMPERATURE_PREFIXES)


# --------------------------------------------------------------------------
# Code extraction
# --------------------------------------------------------------------------
FENCE = re.compile(r"```[ \t]*(?:python|py)?[ \t]*\n(.*?)```", re.S | re.I)


def extract_code(text):
    candidates = []
    for block in FENCE.findall(text):
        try:
            ast.parse(block)
            candidates.append(block)
        except SyntaxError:
            pass
    if candidates:
        return max(candidates, key=len), f"fenced:{len(candidates)}"
    try:
        ast.parse(text)
        return text, "whole_answer"
    except SyntaxError:
        return None, "failed"


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
def call_with_retry(client, kwargs, attempts=5):
    for i in range(attempts):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:                       # rate limits, timeouts, 5xx
            name = type(e).__name__
            if name in ("AuthenticationError", "PermissionDeniedError", "NotFoundError",
                        "BadRequestError") or i == attempts - 1:
                raise
            wait = 2 ** i * 5
            print(f"    {name}: retrying in {wait}s")
            time.sleep(wait)


def check_models(client, models):
    ok = []
    for m in models:
        try:
            client.models.retrieve(m)
            ok.append(m)
            print(f"[OK] model available: {m}")
        except Exception as e:
            print(f"[UNAVAILABLE] {m}: {type(e).__name__}: {e}")
    return ok


def safe(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=10, help="samples per model and exercise (default 10)")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--exercises", nargs="+", default=list(EXERCISES), choices=list(EXERCISES))
    ap.add_argument("--out", default="llm_samples", help="output folder (default llm_samples)")
    ap.add_argument("--dry-run", action="store_true", help="show plan and estimate, make no API calls")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = ap.parse_args()

    prompts = {ex: load_prompt(EXERCISES[ex]) for ex in args.exercises}
    out = (HERE / args.out) if not os.path.isabs(args.out) else pathlib.Path(args.out)

    # ---- plan -------------------------------------------------------------
    todo = []
    for ex in args.exercises:
        for m in args.models:
            for k in range(1, args.n + 1):
                raw = out / "raw" / ex / safe(m) / f"sample_{k:02d}.json"
                if not raw.exists():
                    todo.append((ex, m, k))
    approx_in = {ex: (len(s) + len(u)) // 4 for ex, (s, u) in prompts.items()}
    print(f"Exercises: {args.exercises} | models: {args.models} | n = {args.n}")
    print(f"Calls pending: {len(todo)} (already saved: {len(args.exercises) * len(args.models) * args.n - len(todo)})")
    for ex in args.exercises:
        print(f"  {ex}: ~{approx_in[ex]} input tokens per call; output is typically 1,000-4,000 tokens"
              f" (more for reasoning models)")
    print("  Check current per-token prices for each model before running.")
    if args.dry_run:
        for ex, (s, u) in prompts.items():
            print(f"\n--- {ex} prompt sha256: {hashlib.sha256((s + u).encode()).hexdigest()[:16]}")
            print(f"[system] {s}\n[user, first 300 chars] {u[:300]}...")
        return
    if not todo:
        print("Nothing to do.")
        return
    if not args.yes and input("Proceed? [y/N] ").strip().lower() != "y":
        return

    # ---- run --------------------------------------------------------------
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    requested = sorted({m for _, m, _ in todo})
    available = set(check_models(client, requested))
    out.mkdir(parents=True, exist_ok=True)
    missing = [m for m in requested if m not in available]
    if missing:   # keep a record for the threats-to-validity section
        with open(out / "unavailable_models.txt", "a", encoding="utf-8") as f:
            stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            f.writelines(f"{stamp}\t{m}\n" for m in missing)
    manifest = out / "manifest.csv"
    if manifest.exists():   # upgrade a manifest written by an earlier version of this script
        with open(manifest, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            old_rows, old_fields = list(reader), reader.fieldnames or []
        if "status" not in old_fields:
            with open(manifest, "w", newline="", encoding="utf-8") as f:
                w0 = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
                w0.writeheader()
                for r in old_rows:
                    w0.writerow({**{k: r.get(k, "") for k in MANIFEST_FIELDS}, "status": "ok"})
    new_manifest = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as mf:
        w = csv.DictWriter(mf, fieldnames=MANIFEST_FIELDS)
        if new_manifest:
            w.writeheader()
        for ex, m, k in todo:
            if m not in available:
                continue
            system, user = prompts[ex]
            kwargs = {"model": m, "messages": [{"role": "system", "content": system},
                                               {"role": "user", "content": user}]}
            if supports_temperature(m):
                kwargs["temperature"] = 0.0
            print(f"[{ex}] {m} sample {k:02d} ...", flush=True)
            started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            try:
                resp = call_with_retry(client, kwargs)
            except Exception as e:
                print(f"    FAILED: {type(e).__name__}: {e}")
                w.writerow({"timestamp_utc": started, "exercise": ex, "model_requested": m,
                            "sample": k, "status": f"failed: {type(e).__name__}"})
                mf.flush()
                if type(e).__name__ == "NotFoundError":   # retired/unknown model: skip the rest
                    available.discard(m)
                    with open(out / "unavailable_models.txt", "a", encoding="utf-8") as f:
                        f.write(f"{started}\t{m}\t{e}\n")
                    print(f"    {m} is not available for chat completions; skipping its remaining samples.")
                continue
            text = resp.choices[0].message.content or ""
            raw_dir = out / "raw" / ex / safe(m)
            code_dir = out / "code" / ex / safe(m)
            raw_dir.mkdir(parents=True, exist_ok=True)
            code_dir.mkdir(parents=True, exist_ok=True)
            base = f"sample_{k:02d}"
            (raw_dir / f"{base}.md").write_text(text, encoding="utf-8")
            record = {"request": {k2: v for k2, v in kwargs.items() if k2 != "messages"},
                      "messages": kwargs["messages"], "requested_at_utc": started,
                      "response": resp.model_dump()}
            (raw_dir / f"{base}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False),
                                                  encoding="utf-8")
            code, how = extract_code(text)
            code_file = ""
            if code is not None:
                code_file = str((code_dir / f"{base}.py").relative_to(out))
                (code_dir / f"{base}.py").write_text(
                    f"# Extracted automatically from {base}.md by generate_samples.py ({how})\n{code}",
                    encoding="utf-8")
            usage = resp.usage
            details = getattr(usage, "completion_tokens_details", None) if usage else None
            w.writerow({
                "timestamp_utc": started, "exercise": ex, "model_requested": m,
                "model_returned": resp.model, "system_fingerprint": getattr(resp, "system_fingerprint", "") or "",
                "sample": k, "temperature_sent": kwargs.get("temperature", "default"),
                "prompt_sha256": hashlib.sha256((system + user).encode()).hexdigest(),
                "prompt_tokens": getattr(usage, "prompt_tokens", ""),
                "completion_tokens": getattr(usage, "completion_tokens", ""),
                "reasoning_tokens": getattr(details, "reasoning_tokens", "") if details else "",
                "finish_reason": resp.choices[0].finish_reason, "extraction": how,
                "code_file": code_file, "raw_file": str((raw_dir / f"{base}.json").relative_to(out)),
                "status": "ok",
            })
            mf.flush()
            print(f"    model={resp.model} tokens={getattr(usage, 'completion_tokens', '?')} extraction={how}")
    print(f"\nDone. Send the whole '{out.name}' folder (zip it) for the analysis.")


if __name__ == "__main__":
    main()
