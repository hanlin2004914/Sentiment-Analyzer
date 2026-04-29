import os
import json
from datetime import datetime

ERROR_LOG = "error_log.json"


def log_error(question_id, model, predicted, expected, error_type, notes=""):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question_id": question_id,
        "model": model,
        "predicted": predicted,
        "expected": expected,
        "error_type": error_type,
        "notes": notes,
    }

    entries = load_errors()
    entries.append(entry)

    with open(ERROR_LOG, "w") as f:
        json.dump(entries, f, indent=2)


def load_errors():
    if not os.path.exists(ERROR_LOG):
        return []
    with open(ERROR_LOG, "r") as f:
        return json.load(f)


def get_errors_by_type():
    entries = load_errors()
    by_type = {}
    for e in entries:
        t = e.get("error_type", "unknown")
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(e)
    return by_type


def get_errors_by_model(model_name):
    entries = load_errors()
    return [e for e in entries if e.get("model") == model_name]


def print_error_summary():
    by_type = get_errors_by_type()
    if not by_type:
        print("No errors logged yet.")
        return

    total = sum(len(v) for v in by_type.values())
    print(f"\nError Summary ({total} total)")
    print("-" * 40)
    for error_type, entries in sorted(by_type.items()):
        print(f"  {error_type}: {len(entries)}")


if __name__ == "__main__":
    # demo
    log_error(
        question_id="sa_005",
        model="llama3.2",
        predicted="positive",
        expected="negative",
        error_type="wrong_target",
        notes="Model focused on revenue growth instead of the expectation miss",
    )
    log_error(
        question_id="sa_006",
        model="llama3.2",
        predicted="neutral",
        expected="negative",
        error_type="missing_context",
        notes="Did not recognize reverse stock split as negative",
    )
    print_error_summary()