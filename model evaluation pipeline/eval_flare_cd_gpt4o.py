import os
import re
import json
from collections import Counter
from datasets import load_dataset
from openai import OpenAI
from tqdm import tqdm

DATASET_NAME = "ChanceFocus/flare-cd"
MODEL_NAME = "gpt-4o"
SPLIT = "test"
MAX_SAMPLES = None
OUTPUT_FILE = "flare_cd_gpt4o_results.jsonl"

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def normalize_text(s: str) -> str:
    s = (s or "").strip().replace("\r\n", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    return s


def get_gold(example):
    if "answer" in example and example["answer"]:
        return example["answer"]
    if "label" in example and example["label"]:
        if isinstance(example["label"], list):
            return "\n".join(str(x) for x in example["label"])
        return str(example["label"])
    raise ValueError("No gold field found.")


def get_prompt(example):
    if "query" in example and example["query"]:
        return example["query"]
    if "text" in example and example["text"]:
        return example["text"]
    raise ValueError("No prompt field found.")


def parse_lines(s: str):
    return [x for x in (normalize_text(t) for t in s.split("\n")) if x]


def multiset_f1(pred_lines, gold_lines):
    pred_counter = Counter(pred_lines)
    gold_counter = Counter(gold_lines)
    overlap = sum((pred_counter & gold_counter).values())
    p = overlap / max(len(pred_lines), 1)
    r = overlap / max(len(gold_lines), 1)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def call_gpt4o(prompt: str) -> str:
    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        temperature=0
    )
    return response.output_text.strip()


def main():
    ds = load_dataset(DATASET_NAME, split=SPLIT)
    if MAX_SAMPLES:
        ds = ds.select(range(min(MAX_SAMPLES, len(ds))))

    em_sum, f1_sum = 0, 0.0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ex in tqdm(ds, desc=DATASET_NAME):
            prompt = get_prompt(ex)
            gold = normalize_text(get_gold(ex))
            pred = normalize_text(call_gpt4o(prompt))

            em = int(pred == gold)
            f1 = multiset_f1(parse_lines(pred), parse_lines(gold))

            em_sum += em
            f1_sum += f1

            f.write(json.dumps({
                "id": ex.get("id"),
                "gold": gold,
                "pred": pred,
                "exact_match": em,
                "line_f1": f1
            }, ensure_ascii=False) + "\n")

    n = len(ds)
    print({
        "dataset": DATASET_NAME,
        "model": MODEL_NAME,
        "samples": n,
        "exact_match": em_sum / n,
        "avg_line_f1": f1_sum / n
    })


if __name__ == "__main__":
    main()
