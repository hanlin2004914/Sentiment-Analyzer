import os
import json
import time
import platform
import getpass
import pandas as pd
from tqdm import tqdm
from sklearn.metrics import accuracy_score, f1_score
from datasets import load_dataset, Dataset
from anthropic import Anthropic

# ==========================================
# 1. CONFIGURATION & AUTHENTICATION
# ==========================================
# In 2026, we use the latest Sonnet model for the best price/performance ratio
MODEL = "claude-3-5-sonnet-latest"
LABELS = ["negative", "neutral", "positive"]

# Get API Key
api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("API_KEY")
if not api_key:
    api_key = getpass.getpass("Paste your Anthropic API key: ")
os.environ["ANTHROPIC_API_KEY"] = api_key

# Setup paths for saving results
run_tag = f"flare_fpb_claude_{MODEL.replace('-', '_')}"
save_dir = "./content" if platform.system() == "Linux" else "./output"
os.makedirs(save_dir, exist_ok=True)

pred_path = f"{save_dir}/{run_tag}_predictions.csv"
err_path = f"{save_dir}/{run_tag}_errors.csv"

# ==========================================
# 2. DATA LOADING & NORMALIZATION
# ==========================================
print("Loading flare-fpb dataset from Hugging Face...")
ds_raw = load_dataset("TheFinAI/flare-fpb", split="test")

# Map various possible label formats to our standard set
_alias = {
    "pos": "positive", "neg": "negative", "neu": "neutral",
    "bullish": "positive", "bearish": "negative"
}


def _norm_label(v):
    if v is None: return None
    # Handle numeric labels (0, 1, 2)
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        i = int(v)
        return LABELS[i] if 0 <= i < len(LABELS) else None
    # Handle string labels
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
# 3. CLAUDE API HELPER
# ==========================================
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def ask_claude_once(sentence):
    """
    Calls Claude using the Messages API.
    We use 'prefilling' to ensure Claude starts with a JSON brace.
    """
    system_prompt = "You are a financial sentiment analyzer. You must output only valid JSON."
    user_prompt = (
        f"Task: Classify the sentiment of this sentence into exactly one of: {', '.join(LABELS)}.\n\n"
        f"Sentence: {sentence}\n\n"
        "Return ONLY a JSON object like this: {\"label\": \"positive\"}"
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=128,
            temperature=0.0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": "{"}  # Prefilling to force JSON
            ]
        )
        # Add back the opening brace we prefilled
        raw_json = "{" + response.content[0].text

        # Parse and validate
        obj = json.loads(raw_json)
        pred = str(obj.get("label")).lower()
        return pred if pred in LABELS else "UNKNOWN"

    except Exception as e:
        raise RuntimeError(f"Claude API Error: {e}")


def ask_claude_with_retry(sentence):
    delay = 1.0
    for attempt in range(5):
        try:
            return ask_claude_once(sentence)
        except Exception as e:
            # Retry on rate limits (429) or overloaded servers (529/500)
            if any(x in str(e).lower() for x in ["429", "rate", "limit", "overloaded", "529"]):
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise e
    return "UNKNOWN"


# ==========================================
# 4. EXECUTION LOOP (WITH RESUME LOGIC)
# ==========================================
rows_done = []
done_idx = set()
if os.path.exists(pred_path):
    old = pd.read_csv(pred_path)
    rows_done = old.to_dict("records")
    done_idx = set(old["row_idx"].tolist())
    print(f"Resuming: found {len(done_idx)} existing predictions.")

buf = []
err_rows = []
save_every = 25  # Save to CSV every 25 rows

print(f"Starting evaluation of {MODEL}...")
for i in tqdm(range(len(ds))):
    if i in done_idx: continue

    row = ds[i]
    try:
        pred = ask_claude_with_retry(row["text"])
    except Exception as e:
        pred = "ERROR"
        err_rows.append({"row_idx": i, "error": str(e), "text": row["text"]})

    buf.append({
        "row_idx": i,
        "text": row["text"],
        "pred": pred,
        "label": row["answer"]
    })

    # Periodic checkpoint
    if len(buf) % save_every == 0:
        pd.DataFrame(rows_done + buf).to_csv(pred_path, index=False)
        if err_rows: pd.DataFrame(err_rows).to_csv(err_path, index=False)

# Final Save
final_df = pd.DataFrame(rows_done + buf).sort_values("row_idx")
final_df.to_csv(pred_path, index=False)

# ==========================================
# 5. FINAL EVALUATION REPORT
# ==========================================
print("\n" + "=" * 30)
print("      CLAUDE EVALUATION      ")
print("=" * 30)

# Only evaluate rows that didn't error out
eval_df = final_df[final_df["pred"].isin(LABELS)]

if not eval_df.empty:
    acc = accuracy_score(eval_df["label"], eval_df["pred"])
    f1 = f1_score(eval_df["label"], eval_df["pred"], average="macro")

    print(f"Model:         {MODEL}")
    print(f"Accuracy:      {acc:.4f}")
    print(f"Macro F1:      {f1:.4f}")
    print(f"Processed:     {len(eval_df)} / {len(ds)}")

    if len(eval_df) < len(ds):
        print(f"Note: {len(ds) - len(eval_df)} samples were skipped due to errors.")
else:
    print("No valid predictions were found to evaluate.")