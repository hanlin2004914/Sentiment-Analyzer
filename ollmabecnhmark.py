import os
import json
import time
import re
import platform
import requests
import pandas as pd

from tqdm import tqdm
from datasets import load_dataset, Dataset
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from importlib.metadata import version, PackageNotFoundError


LABELS = ["negative", "neutral", "positive"]

MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/generate"

SAVE_DIR = "."
RUN_TAG = f"flare_fpb_ollama_{MODEL.replace('/', '_').replace(':', '_')}"

PRED_PATH = f"{SAVE_DIR}/{RUN_TAG}_predictions.csv"
META_PATH = f"{SAVE_DIR}/{RUN_TAG}_metadata.json"
ERR_PATH = f"{SAVE_DIR}/{RUN_TAG}_errors.csv"


def ver(pkg):
    try:
        return version(pkg)
    except PackageNotFoundError:
        return "not-installed"


def norm_label(v):
    alias = {
        "pos": "positive",
        "neg": "negative",
        "neu": "neutral",
        "bullish": "positive",
        "bearish": "negative",
    }

    if v is None:
        return None

    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        i = int(v)
        if 0 <= i < len(LABELS):
            return LABELS[i]
        return None

    s = str(v).strip().lower()
    s = alias.get(s, s)

    if s in LABELS:
        return s

    return None


def map_row(x):
    text = (
        x.get("text")
        or x.get("sentence")
        or x.get("content")
        or x.get("input")
        or ""
    )

    label = norm_label(x.get("label", x.get("labels", x.get("answer"))))

    return {
        "text": text,
        "choices": LABELS,
        "answer": label,
    }


def load_flare_fpb():
    ds_raw = load_dataset("TheFinAI/flare-fpb", split="test")
    print("Loaded flare-fpb test:", len(ds_raw), "columns:", ds_raw.column_names)

    ds = Dataset.from_list([{**r, **map_row(r)} for r in ds_raw])

    bad = [i for i, r in enumerate(ds) if r["answer"] not in LABELS]
    print("Samples with unusable label:", len(bad))

    if len(bad) > 0:
        raise ValueError("Found unparseable labels. Check the field mapping.")

    return ds


def save_metadata():
    meta = {
        "dataset": "TheFinAI/flare-fpb",
        "split": "test",
        "labels": list(LABELS),
        "model": MODEL,
        "ollama_url": OLLAMA_URL,
        "datasets_version": ver("datasets"),
        "pandas": ver("pandas"),
        "tqdm": ver("tqdm"),
        "requests": ver("requests"),
        "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "python": platform.python_version(),
        "note": "Ollama local benchmark using strict JSON output",
    }

    os.makedirs(SAVE_DIR, exist_ok=True)

    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print("Meta saved ->", META_PATH)
    print("MODEL:", MODEL)
    print("OLLAMA_URL:", OLLAMA_URL)


def strip_code_fences(s):
    s = s.strip()

    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)

    return s.strip()


def make_prompt(sentence, choices=("negative", "neutral", "positive")):
    return (
        "Task: classify the financial sentiment of the sentence.\n\n"
        f"Choices: {', '.join(choices)}\n\n"
        f"Sentence: {sentence}\n\n"
        "Return ONLY a JSON object on one line exactly like this:\n"
        "{\"label\":\"negative\"}\n\n"
        "The label must be exactly one of: negative, neutral, positive.\n"
        "No explanation. No markdown. No code fences."
    )


def ask_ollama_once(sentence, choices=("negative", "neutral", "positive")):
    prompt = make_prompt(sentence, choices)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0
            }
        },
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(f"Ollama error: {response.status_code}: {response.text}")

    data = response.json()
    text = data.get("response", "")

    if not text:
        raise RuntimeError(f"No response text from Ollama: {data}")

    text = strip_code_fences(text)

    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON from Ollama: {text}")

    label = obj.get("label")

    if label not in choices:
        raise RuntimeError(f"Invalid label from Ollama: {label}")

    return label, text


def ask_ollama(sentence, choices=("negative", "neutral", "positive")):
    delay = 1
    last_error = None

    for attempt in range(3):
        try:
            return ask_ollama_once(sentence, choices)
        except Exception as e:
            last_error = e
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"Failed after retries: {last_error}")


def run_benchmark(ds):
    rows_done = []
    done_idx = set()

    if os.path.exists(PRED_PATH):
        old = pd.read_csv(PRED_PATH)

        if "row_idx" in old.columns:
            rows_done = old.to_dict("records")
            done_idx = set(old["row_idx"].tolist())
            print(f"[resume] loaded {len(done_idx)} completed rows.")

    err_rows = []
    buf = []
    save_every = 50

    total = len(ds)

    for i in tqdm(range(total)):
        if i in done_idx:
            continue

        x = ds[i]
        text = x["text"]
        gold = x["answer"]

        start_time = time.time()

        try:
            pred, raw = ask_ollama(text, LABELS)
            error = ""
        except Exception as e:
            pred = "UNKNOWN"
            raw = ""
            error = f"{type(e).__name__}: {e}"

            err_rows.append({
                "row_idx": i,
                "id": x.get("id", i),
                "error": error,
                "text": text,
            })

        elapsed = time.time() - start_time

        buf.append({
            "row_idx": i,
            "id": x.get("id", i),
            "text": text,
            "pred_raw": raw,
            "pred": pred,
            "label": gold,
            "correct": pred == gold,
            "seconds": elapsed,
            "error": error,
        })

        if len(buf) % save_every == 0:
            out = pd.DataFrame(rows_done + buf).sort_values("row_idx")
            out.to_csv(PRED_PATH, index=False)

            if err_rows:
                pd.DataFrame(err_rows).to_csv(ERR_PATH, index=False)

            print(f"[checkpoint] saved {len(out)}/{total} -> {PRED_PATH}")

    out = pd.DataFrame(rows_done + buf).sort_values("row_idx")
    out.to_csv(PRED_PATH, index=False)

    if err_rows:
        pd.DataFrame(err_rows).to_csv(ERR_PATH, index=False)

    print("[done] saved ->", PRED_PATH)

    if os.path.exists(ERR_PATH):
        print("[errors] saved ->", ERR_PATH)


def evaluate_results():
    df = pd.read_csv(PRED_PATH).sort_values("row_idx").drop_duplicates("row_idx", keep="last")

    ok = df[df["pred"] != "UNKNOWN"].copy()

    acc = accuracy_score(ok["label"], ok["pred"])
    f1_macro = f1_score(ok["label"], ok["pred"], labels=LABELS, average="macro", zero_division=0)
    f1_weighted = f1_score(ok["label"], ok["pred"], labels=LABELS, average="weighted", zero_division=0)

    print("\n===== RESULTS =====")
    print("Model:", MODEL)
    print("Total rows:", len(df))
    print("Successful rows:", len(ok))
    print("Unknown/error rows:", len(df) - len(ok))
    print(f"Accuracy: {acc:.4f}")
    print(f"Macro F1: {f1_macro:.4f}")
    print(f"Weighted F1: {f1_weighted:.4f}")

    print("\nClassification report:")
    print(classification_report(ok["label"], ok["pred"], labels=LABELS, zero_division=0))

    print("\nConfusion matrix:")
    print(confusion_matrix(ok["label"], ok["pred"], labels=LABELS))

    wrong = ok[ok["label"] != ok["pred"]]
    wrong_path = f"{SAVE_DIR}/{RUN_TAG}_wrong_predictions.csv"
    wrong.to_csv(wrong_path, index=False)

    print("\nWrong predictions:", len(wrong))
    print("Wrong predictions saved ->", wrong_path)


def main():
    save_metadata()
    ds = load_flare_fpb()
    run_benchmark(ds)
    evaluate_results()


if __name__ == "__main__":
    main()