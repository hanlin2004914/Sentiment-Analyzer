import os
import json
import time
import re
import pandas as pd

from tqdm import tqdm
from sklearn.metrics import accuracy_score, f1_score
from anthropic import Anthropic

from docx import Document
from PyPDF2 import PdfReader


# -------------------------
# CONFIG
# -------------------------

MODEL = "claude-3-opus-20240229"
LABELS = ["negative", "neutral", "positive"]

INPUT_PATH = "your_dataset.pdf"   # change this
SAVE_PATH = "benchmark_results.csv"
ERROR_PATH = "errors.csv"


client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# -------------------------
# DATA LOADERS
# -------------------------

def load_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    return [{"text": l, "label": None} for l in lines]


def load_csv(path):
    df = pd.read_csv(path)

    if "text" not in df.columns:
        raise ValueError("CSV must contain 'text' column")

    if "label" not in df.columns:
        df["label"] = None

    return df.to_dict("records")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_docx(path):
    doc = Document(path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    sentences = text.split("\n")
    return [{"text": s.strip(), "label": None} for s in sentences if s.strip()]


def load_pdf(path):
    reader = PdfReader(path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() + "\n"

    sentences = text.split("\n")
    return [{"text": s.strip(), "label": None} for s in sentences if s.strip()]


def load_dataset(path):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".txt":
        return load_txt(path)
    elif ext == ".csv":
        return load_csv(path)
    elif ext == ".json":
        return load_json(path)
    elif ext == ".docx":
        return load_docx(path)
    elif ext == ".pdf":
        return load_pdf(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# -------------------------
# MODEL CALL
# -------------------------

def clean_json(text):
    text = text.strip()
    text = re.sub(r"^```.*?\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text


def build_prompt(text):
    return f"""
Classify the sentiment of this text.

Text: {text}

Return ONLY JSON:
{{"label":"negative|neutral|positive"}}
""".strip()


def call_model(text):
    try:
        res = client.messages.create(
            model=MODEL,
            max_tokens=50,
            temperature=0,
            messages=[
                {"role": "user", "content": build_prompt(text)}
            ]
        )

        output = res.content[0].text
        output = clean_json(output)

        label = json.loads(output)["label"]

        if label not in LABELS:
            return "UNKNOWN", output

        return label, output

    except Exception as e:
        return "UNKNOWN", str(e)


# -------------------------
# BENCHMARK LOOP
# -------------------------

def run_benchmark(data):
    results = []
    errors = []

    for i, row in enumerate(tqdm(data)):
        text = row["text"]
        gold = row.get("label")

        start = time.time()
        pred, raw = call_model(text)
        latency = time.time() - start

        correct = None
        if gold is not None:
            correct = pred == gold

        results.append({
            "text": text,
            "gold": gold,
            "pred": pred,
            "correct": correct,
            "latency": latency,
            "raw": raw
        })

        if pred == "UNKNOWN":
            errors.append({
                "text": text,
                "error": raw
            })

        if i % 50 == 0:
            pd.DataFrame(results).to_csv(SAVE_PATH, index=False)
            if errors:
                pd.DataFrame(errors).to_csv(ERROR_PATH, index=False)

    df = pd.DataFrame(results)
    df.to_csv(SAVE_PATH, index=False)

    if errors:
        pd.DataFrame(errors).to_csv(ERROR_PATH, index=False)

    return df


# -------------------------
# METRICS
# -------------------------

def evaluate(df):
    df_eval = df[(df["gold"].notna()) & (df["pred"] != "UNKNOWN")]

    if len(df_eval) == 0:
        print("\nNo labeled data available for evaluation.")
        return

    acc = accuracy_score(df_eval["gold"], df_eval["pred"])
    f1 = f1_score(df_eval["gold"], df_eval["pred"], average="macro")

    print("\n===== RESULTS =====")
    print("Model:", MODEL)
    print("Samples:", len(df))
    print("Evaluated:", len(df_eval))
    print("Accuracy:", round(acc, 4))
    print("Macro F1:", round(f1, 4))

    wrong = df_eval[df_eval["gold"] != df_eval["pred"]]
    print("Wrong predictions:", len(wrong))


# -------------------------
# MAIN
# -------------------------

def main():
    print("Loading dataset from:", INPUT_PATH)
    data = load_dataset(INPUT_PATH)

    print("Total samples:", len(data))
    print("Running model:", MODEL)

    df = run_benchmark(data)

    evaluate(df)


if __name__ == "__main__":
    main()