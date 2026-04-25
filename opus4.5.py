import os
import json
import time
import re
import pandas as pd

from datasets import load_dataset
from tqdm import tqdm
from sklearn.metrics import accuracy_score, f1_score
from anthropic import Anthropic


MODEL = "claude-3-opus-20240229"
LABELS = ["negative", "neutral", "positive"]

SAVE_PATH = "opus45_results.csv"


# -------------------------
# DATASET
# -------------------------

def load_data():
    ds = load_dataset("TheFinAI/flare-fpb", split="test")

    def normalize(row):
        text = row.get("text") or row.get("sentence") or ""

        label_map = {
            "pos": "positive",
            "neg": "negative",
            "neu": "neutral"
        }

        raw = row.get("label")
        if isinstance(raw, int):
            label = LABELS[raw]
        else:
            label = label_map.get(str(raw).lower(), str(raw).lower())

        return {"text": text, "label": label}

    data = [normalize(r) for r in ds]
    return data


# -------------------------
# MODEL CALL
# -------------------------

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def clean_json(text):
    text = text.strip()
    text = re.sub(r"^```.*?\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text


def build_prompt(text):
    return f"""
Classify the sentiment of this sentence.

Sentence: {text}

Return ONLY JSON:
{{"label":"negative|neutral|positive"}}
""".strip()


def call_model(text):
    prompt = build_prompt(text)

    res = client.messages.create(
        model=MODEL,
        max_tokens=50,
        temperature=0,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    output = res.content[0].text
    output = clean_json(output)

    try:
        label = json.loads(output)["label"]
        if label not in LABELS:
            return "UNKNOWN"
        return label
    except:
        return "UNKNOWN"


# -------------------------
# BENCHMARK LOOP
# -------------------------

def run_eval(data):
    results = []

    for i, row in enumerate(tqdm(data)):
        text = row["text"]
        gold = row["label"]

        start = time.time()
        pred = call_model(text)
        latency = time.time() - start

        results.append({
            "text": text,
            "gold": gold,
            "pred": pred,
            "correct": pred == gold,
            "latency": latency
        })

        if i % 50 == 0:
            pd.DataFrame(results).to_csv(SAVE_PATH, index=False)

    df = pd.DataFrame(results)
    df.to_csv(SAVE_PATH, index=False)

    return df


# -------------------------
# METRICS
# -------------------------

def evaluate(df):
    df = df[df["pred"] != "UNKNOWN"]

    acc = accuracy_score(df["gold"], df["pred"])
    f1 = f1_score(df["gold"], df["pred"], average="macro")

    print("\nRESULTS")
    print("Accuracy:", round(acc, 4))
    print("Macro F1:", round(f1, 4))

    wrong = df[df["gold"] != df["pred"]]
    print("Wrong:", len(wrong))


# -------------------------
# MAIN
# -------------------------

def main():
    print("Loading dataset...")
    data = load_data()

    print("Running benchmark on", MODEL)
    df = run_eval(data)

    evaluate(df)


if __name__ == "__main__":
    main()