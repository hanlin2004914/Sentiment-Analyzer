import json
import os

RESULTS_DIR = "results"

def load_result(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def compare_models(result_files):
    summaries = []
    for filepath in result_files:
        data = load_result(filepath)
        model = data.get("model", "unknown")
        metrics = data.get("metrics", {})
        accuracy = metrics.get("accuracy", 0)
        per_task = metrics.get("per_task", {})

        summaries.append({
            "model": model,
            "accuracy": round(accuracy * 100, 2),
            "tasks": {
                task: round(info.get("accuracy", 0) * 100, 2)
                for task, info in per_task.items()
            }
        })

    summaries.sort(key=lambda x: x["accuracy"], reverse=True)
    return summaries

def print_comparison(summaries):
    if not summaries:
        print("No results to compare.")
        return

    print(f"\n{'Model':<25} {'Accuracy':>10}")
    print("-" * 37)
    for s in summaries:
        print(f"{s['model']:<25} {s['accuracy']:>9.1f}%")
        for task, score in s["tasks"].items():
            print(f"  {task:<23} {score:>9.1f}%")

def get_result_files():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        return []
    return [
        os.path.join(RESULTS_DIR, f)
        for f in os.listdir(RESULTS_DIR)
        if f.endswith(".json")
    ]

if __name__ == "__main__":
    files = get_result_files()
    if files:
        summaries = compare_models(files)
        print_comparison(summaries)
    else:
        print(f"No result files found in {RESULTS_DIR}/")
        print("Run an evaluation first to generate results.")