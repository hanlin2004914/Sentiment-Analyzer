"""
Batch runner: evaluate o3 on all supported FLARE datasets sequentially.

Usage:
    python run_all_flare.py                  # full test split
    python run_all_flare.py --max-samples 20 # smoke test (20 samples each)

Outputs:
    Per-dataset: {slug}_o3_predictions.csv, {slug}_o3_metrics.json
    Summary:     flare_all_o3_summary.json
"""

import json
import subprocess
import sys
from pathlib import Path

DATASETS = [
    "flare-ner",
    "flare-finred",
    "flare-causal20-sc",
    "flare-cd",
    "flare-fnxl",
    "flare-fsrl",
]

SCRIPT = Path(__file__).resolve().parent / "o3_flare_ner.py"


def main():
    extra_args = sys.argv[1:]
    results = {}

    for dataset in DATASETS:
        print(f"\n{'=' * 60}")
        print(f"  Running: {dataset}")
        print(f"{'=' * 60}\n")

        cmd = [sys.executable, str(SCRIPT), "--dataset", dataset] + extra_args
        ret = subprocess.run(cmd)

        slug = dataset.replace("-", "_")
        metrics_path = SCRIPT.parent / f"{slug}_o3_metrics.json"
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
            results[dataset] = metrics
            print(f"\n  >> {dataset} done: F1={metrics.get('f1', 0):.4f}")
        else:
            results[dataset] = {"error": f"exit_code={ret.returncode}"}
            print(f"\n  >> {dataset} FAILED (exit code {ret.returncode})")

    print(f"\n\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    print(f"{'Dataset':<22} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Samples':>10}")
    print("-" * 64)
    for dataset in DATASETS:
        m = results.get(dataset, {})
        if "error" in m:
            print(f"{dataset:<22} {'FAILED':>10}")
        else:
            print(
                f"{dataset:<22} "
                f"{m.get('precision', 0):>10.4f} "
                f"{m.get('recall', 0):>10.4f} "
                f"{m.get('f1', 0):>10.4f} "
                f"{m.get('total_samples', 0):>10}"
            )
    print()

    summary_path = SCRIPT.parent / "flare_all_o3_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
