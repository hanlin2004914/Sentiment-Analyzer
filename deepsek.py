import os
import json
import time
import platform
import getpass
import re
import pandas as pd
from tqdm import tqdm
from sklearn.metrics import accuracy_score, f1_score
from datasets import load_dataset, Dataset
from openai import OpenAI
from importlib.metadata import version, PackageNotFoundError

# ==========================================
# 1. CONFIGURATION & AUTHENTICATION
# ==========================================
MODEL = "deepseek-chat"  # Or "deepseek-reasoner" for R1
BASE_URL = "https://api.deepseek.com"
LABELS = ["negative", "neutral", "positive"]

# Get API Key
api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
if not api_key:
    api_key = getpass.getpass("Paste your DeepSeek API key: ")
os.environ["DEEPSEEK_API_KEY"] = api_key

# Setup paths
run_tag = f"flare_fpb_deepseek_{MODEL.replace('/', '_')}"
save_dir = "./content" if platform.system() == "Linux" else "./output"
os.makedirs(save_dir, exist_ok=True)

pred_path = f"{save_dir}/{run_tag}_predictions.csv"
err_path = f"{save_dir}/{run_tag}_errors.csv"

# ==========================================
# 2. DATA LOADING & NORMALIZATION
# ==========================================
print("Loading dataset...")
ds_raw = load_dataset("TheFinAI/flare-fpb", split="test")

_alias = {
    "pos": "positive", "neg": "negative", "neu": "neutral",
    "bullish": "positive", "bearish": "negative"
}


def _norm_label(v):
    if v is None: return None
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        i = int(v)
        return LABELS[i] if 0 <= i < len(LABELS) else None
    s = str(v).strip().lower()
    s = _alias.get(s, s)
    return s if s in LABELS else None


def _map_row(x):
    text = x.get("text") or x.get("sentence") or x.get("content") or x.get("input") or ""
    lab = _norm_label(x.get("label", x.get("labels", x.get("answer"))))
    return {"text": text, "choices": LABELS, "answer": lab}


ds = Dataset.from_list([{**r, **_map_row(r)} for r in ds_raw])
print(f"Dataset prepared: {len(ds)} samples.")

# ==========================================
# 3. DEEPSEEK CLIENT & HELPERS
# ==========================================
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=BASE_URL)


def _make_prompt(sentence):
    return (
        f"Task: Classify the sentiment of this financial sentence as exactly one of: {', '.join(LABELS)}.\n\n"
        f"Sentence: {sentence}\n\n"
        "Return ONLY a JSON object in this format:\n"
        '{"label": "sentiment_here"}'
    )


def ask_deepseek_once(sentence, max_tok=128):
    user_text = _make_prompt(sentence)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a financial analyst. Respond only in JSON."},
                {"role": "user", "content": user_text},
            ],
            response_format={'type': 'json_object'},
            temperature=0.0,
            max_tokens=max_tok,
        )
        txt = response.choices[0].message.content
        obj = json.loads(txt)
        lab = str(obj.get("label")).lower()
        return lab if lab in LABELS else "UNKNOWN"
    except Exception as e:
        raise RuntimeError(f"DeepSeek Error: {e}")


def ask_deepseek_with_retry(sentence):
    delay = 1.0
    for attempt in range(5):
        try:
            return ask_deepseek_once(sentence)
        except Exception as e:
            if any(x in str(e).lower() for x in ["429", "rate", "500", "503"]):
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
    return "UNKNOWN"


# ==========================================
# 4. EXECUTION LOOP
# ==========================================
rows_done = []
done_idx = set()
if os.path.exists(pred_path):
    old = pd.read_csv(pred_path)
    rows_done = old.to_dict("records")
    done_idx = set(old["row_idx"].tolist())
    print(f"Resuming from row {len(done_idx)}")

buf = []
err_rows = []
save_every = 20

for i in tqdm(range(len(ds))):
    if i in done_idx: continue

    row = ds[i]
    try:
        pred = ask_deepseek_with_retry(row["text"])
    except Exception as e:
        pred = "ERROR"
        err_rows.append({"row_idx": i, "error": str(e), "text": row["text"]})

    buf.append({
        "row_idx": i,
        "text": row["text"],
        "pred": pred,
        "label": row["answer"]
    })

    if len(buf) % save_every == 0:
        pd.DataFrame(rows_done + buf).to_csv(pred_path, index=False)
        if err_rows: pd.DataFrame(err_rows).to_csv(err_path, index=False)

# Final Save
final_df = pd.DataFrame(rows_done + buf).sort_values("row_idx")
final_df.to_csv(pred_path, index=False)

# ==========================================
# 5. EVALUATION
# ==========================================
print("\n--- Evaluation Results ---")
eval_df = final_df[final_df["pred"].isin(LABELS)]
if not eval_df.empty:
    acc = accuracy_score(eval_df["label"], eval_df["pred"])
    f1 = f1_score(eval_df["label"], eval_df["pred"], average="macro")
    print(f"Model: {MODEL}")
    print(f"Accuracy: {acc:.4f}")
    print(f"Macro F1: {f1:.4f}")
    print(f"Valid Samples: {len(eval_df)} / {len(final_df)}")
else:
    print("No valid predictions to evaluate.")