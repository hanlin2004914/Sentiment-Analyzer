#!/usr/bin/env python3
"""
Evaluate ChanceFocus/flare-causal20-sc with GPT-5 via the OpenAI Responses API.

Usage:
    export OPENAI_API_KEY="your_api_key"
    python eval_flare_causal20_sc_gpt5.py --model gpt-5 --max-examples 100 --output-dir outputs/eval_flare_causal20_sc_gpt5

Dependencies:
    pip install -U openai datasets

Notes:
    - This script uses the Hugging Face dataset "ChanceFocus/flare-causal20-sc".
    - If the dataset provides a `query` field, that field is sent directly to the model.
    - Predictions and summary metrics are written to the output directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from datasets import load_dataset
from openai import OpenAI


CONFIG = {
    "dataset_name": "ChanceFocus/flare-causal20-sc",
    "task_type": "binary_classification",
    "default_model": "gpt-5",
    "default_split": "test",
    "allowed_entity_labels": [],
    "classification_labels": ['noise', 'causal'],
    "positive_label": 'causal',
}


def normalize_space(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def normalize_for_match(text: Any) -> str:
    return normalize_space(text).lower()


def safe_float(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def f1_score(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def choose_split(dataset_dict, requested: Optional[str]) -> str:
    if requested and requested in dataset_dict:
        return requested
    for candidate in ("test", "valid", "validation", "dev", "train"):
        if candidate in dataset_dict:
            return candidate
    return next(iter(dataset_dict.keys()))


def get_text_column(row: Dict[str, Any]) -> str:
    for key in ("text", "sentence", "input", "content"):
        if key in row and row[key] not in (None, ""):
            return str(row[key])
    return ""


def get_query(row: Dict[str, Any]) -> str:
    query = row.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    text = get_text_column(row)
    task_type = CONFIG["task_type"]
    if task_type == "ner_entities":
        label_str = ", ".join(CONFIG["allowed_entity_labels"])
        return (
            f"Identify all named entities in the text. "
            f"Allowed labels: {label_str}. "
            f"Return one entity per line in the format 'entity, LABEL'. "
            f"If there are no entities, return an empty response.\n\n"
            f"Text: {text}\nAnswer:"
        )
    if task_type == "relation_triples":
        return (
            "Identify all relation triples in the text. "
            "Return one triple per line in the format 'head ; tail ; relation'. "
            "If there are no relations, return an empty response.\n\n"
            f"Text: {text}\nAnswer:"
        )
    if task_type == "binary_classification":
        allowed = ", ".join(CONFIG["classification_labels"])
        return (
            f"Classify the text into exactly one of: {allowed}. "
            "Return only the label.\n\n"
            f"Text: {text}\nAnswer:"
        )
    if task_type == "causal_spans":
        return (
            "Extract causal spans from the sentence. "
            "Return each span on a new line as 'Cause: ...' or 'Effect: ...'. "
            "If there are multiple causes or effects, return each on its own line. "
            "If there are none, return an empty response.\n\n"
            f"Text: {text}\nAnswer:"
        )
    if task_type == "sequence_labels":
        return (
            "Label each token in the text using BIO tags. "
            "Return one token-label pair per line in the format 'token:label'.\n\n"
            f"Text: {text}\nAnswer:"
        )
    raise ValueError(f"Unsupported task type: {task_type}")


def extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: List[str] = []

    output = getattr(response, "output", None)
    if output:
        for item in output:
            content = getattr(item, "content", None)
            if content:
                for block in content:
                    text = getattr(block, "text", None)
                    if isinstance(text, str) and text:
                        parts.append(text)
            text = getattr(item, "text", None)
            if isinstance(text, str) and text:
                parts.append(text)

    if isinstance(response, dict):
        if isinstance(response.get("output_text"), str) and response["output_text"].strip():
            return response["output_text"].strip()

    return "\n".join(part.strip() for part in parts if part.strip()).strip()


def call_model(client: OpenAI, model: str, prompt: str, retries: int = 5, sleep_seconds: float = 1.0) -> str:
    instruction = "Return only the final answer in the requested format. Do not add explanation."
    for attempt in range(retries):
        try:
            response = client.responses.create(
                model=model,
                input=f"{instruction}\n\n{prompt}",
            )
            return extract_response_text(response)
        except Exception as exc:
            if attempt == retries - 1:
                raise
            wait_time = sleep_seconds * (2 ** attempt)
            print(f"[retry] API call failed: {exc}. Sleeping {wait_time:.1f}s ...")
            time.sleep(wait_time)
    raise RuntimeError("Unreachable")


def parse_entity_pairs(text: Any, allowed_labels: Sequence[str]) -> List[Tuple[str, str]]:
    allowed = set(allowed_labels)
    raw = str(text or "").strip()
    if not raw:
        return []

    pairs: List[Tuple[str, str]] = []

    for line in raw.replace("\r", "\n").split("\n"):
        line = line.strip().strip("-*")
        if not line:
            continue
        if ";" in line and line.count(";") >= 2 and "," not in line:
            continue
        if "," in line:
            left, right = line.rsplit(",", 1)
            entity = normalize_space(left)
            label = normalize_space(right).upper()
            if entity and label in allowed:
                pairs.append((normalize_for_match(entity), label))

    if pairs:
        return sorted(set(pairs))

    pattern = re.compile(r"([^,\n]+?),\s*(" + "|".join(map(re.escape, allowed)) + r")\b", re.IGNORECASE)
    for match in pattern.finditer(raw):
        entity = normalize_space(match.group(1))
        label = match.group(2).upper()
        if entity and label in allowed:
            pairs.append((normalize_for_match(entity), label))
    return sorted(set(pairs))


def parse_relation_triples(text: Any) -> List[Tuple[str, str, str]]:
    raw = str(text or "").strip()
    if not raw:
        return []

    triples: List[Tuple[str, str, str]] = []

    lines = [line.strip() for line in raw.replace("\r", "\n").split("\n") if line.strip()]
    for line in lines:
        parts = [normalize_space(p) for p in line.split(";")]
        if len(parts) == 3:
            head, tail, rel = parts
            if head and tail and rel:
                triples.append((normalize_for_match(head), normalize_for_match(tail), normalize_for_match(rel)))
        elif len(parts) > 3 and len(parts) % 3 == 0:
            for i in range(0, len(parts), 3):
                head, tail, rel = parts[i:i+3]
                if head and tail and rel:
                    triples.append((normalize_for_match(head), normalize_for_match(tail), normalize_for_match(rel)))

    if triples:
        return sorted(set(triples))

    pattern = re.compile(r"([^;\n]+?)\s*;\s*([^;\n]+?)\s*;\s*([^;\n]+)")
    for match in pattern.finditer(raw):
        head = normalize_space(match.group(1))
        tail = normalize_space(match.group(2))
        rel = normalize_space(match.group(3))
        if head and tail and rel:
            triples.append((normalize_for_match(head), normalize_for_match(tail), normalize_for_match(rel)))
    return sorted(set(triples))


def parse_binary_label(text: Any) -> str:
    raw = normalize_for_match(text)
    if not raw:
        return ""
    allowed = [normalize_for_match(label) for label in (CONFIG["classification_labels"] or [])]
    for label in allowed:
        if re.search(rf"\b{re.escape(label)}\b", raw):
            return label
    if raw in {"0", "false", "negative", "no"} and "noise" in allowed:
        return "noise"
    if raw in {"1", "true", "positive", "yes"} and "causal" in allowed:
        return "causal"
    return raw.split()[0] if raw.split() else ""


def parse_token_label_pairs(text: Any) -> Tuple[List[str], List[str]]:
    raw = str(text or "")
    if not raw.strip():
        return [], []

    tokens: List[str] = []
    labels: List[str] = []

    for line in raw.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        token, label = line.rsplit(":", 1)
        token = token.strip()
        label = label.strip()
        if not token or not label:
            continue
        tokens.append(token)
        labels.append(label)

    if tokens:
        return tokens, labels

    pattern = re.compile(r"(\S+):([A-Za-z0-9_.\-/]+)")
    for token, label in pattern.findall(raw):
        tokens.append(token)
        labels.append(label)
    return tokens, labels


def spans_from_bio(tokens: Sequence[str], labels: Sequence[str]) -> List[Tuple[str, str]]:
    spans: List[Tuple[str, str]] = []
    current_tokens: List[str] = []
    current_label: Optional[str] = None

    def flush() -> None:
        nonlocal current_tokens, current_label
        if current_tokens and current_label:
            span_text = normalize_for_match(" ".join(current_tokens))
            spans.append((span_text, current_label))
        current_tokens = []
        current_label = None

    for token, label in zip(tokens, labels):
        label = str(label)
        if label == "O":
            flush()
            continue
        if label.startswith("B-"):
            flush()
            current_label = label[2:]
            current_tokens = [token]
        elif label.startswith("I-"):
            role = label[2:]
            if current_label == role and current_tokens:
                current_tokens.append(token)
            else:
                flush()
                current_label = role
                current_tokens = [token]
        else:
            flush()
            current_label = label
            current_tokens = [token]
            flush()
    flush()
    return spans


def labels_only_from_output(text: Any) -> List[str]:
    _, labels = parse_token_label_pairs(text)
    if labels:
        return labels
    raw = str(text or "")
    return re.findall(r"\b(?:O|[BI]-[A-Za-z0-9_.\-/]+)\b", raw)


def parse_causal_span_lines(text: Any) -> List[Tuple[str, str]]:
    raw = str(text or "").strip()
    if not raw:
        return []
    spans: List[Tuple[str, str]] = []
    for line in raw.replace("\r", "\n").split("\n"):
        line = line.strip().strip("-*")
        if not line:
            continue
        match = re.match(r"(?i)\s*(cause|effect)\s*:\s*(.+)", line)
        if match:
            label = match.group(1).upper()
            span_text = normalize_for_match(match.group(2))
            if span_text:
                spans.append((span_text, label))
                continue
        if "," in line:
            left, right = line.rsplit(",", 1)
            label = normalize_space(right).upper()
            if label in {"CAUSE", "EFFECT"}:
                span_text = normalize_for_match(left)
                if span_text:
                    spans.append((span_text, label))
    return sorted(set(spans))


def get_gold_entity_pairs(row: Dict[str, Any]) -> List[Tuple[str, str]]:
    answer = row.get("answer")
    pairs = parse_entity_pairs(answer, CONFIG["allowed_entity_labels"])
    if pairs:
        return pairs
    labels = row.get("label")
    text = get_text_column(row)
    if isinstance(labels, Sequence) and not isinstance(labels, (str, bytes)):
        tokens = text.split()
        if len(tokens) == len(labels):
            return sorted(set(spans_from_bio(tokens, [str(x) for x in labels])))
    return []


def get_gold_relation_triples(row: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    return parse_relation_triples(row.get("answer"))


def get_gold_binary_label(row: Dict[str, Any]) -> str:
    answer = row.get("answer")
    gold = parse_binary_label(answer)
    if gold:
        return gold
    label = row.get("label")
    if isinstance(label, Sequence) and not isinstance(label, (str, bytes)) and label:
        gold = parse_binary_label(label[0])
        if gold:
            return gold
    return parse_binary_label(label)


def get_gold_sequence(row: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    answer_tokens, answer_labels = parse_token_label_pairs(row.get("answer"))
    if answer_tokens and answer_labels:
        return answer_tokens, answer_labels
    label_field = row.get("label")
    text = get_text_column(row)
    if isinstance(label_field, Sequence) and not isinstance(label_field, (str, bytes)):
        labels = [str(x) for x in label_field]
        tokens = text.split()
        if len(tokens) == len(labels):
            return tokens, labels
    return [], []


def get_gold_causal_spans(row: Dict[str, Any]) -> List[Tuple[str, str]]:
    answer_tokens, answer_labels = parse_token_label_pairs(row.get("answer"))
    if answer_tokens and answer_labels:
        spans = spans_from_bio(answer_tokens, answer_labels)
        if spans:
            return sorted(set((span, label) for span, label in spans if label in {"CAUSE", "EFFECT"}))

    answer_spans = parse_causal_span_lines(row.get("answer"))
    if answer_spans:
        return answer_spans

    label_field = row.get("label")
    text = get_text_column(row)
    if isinstance(label_field, Sequence) and not isinstance(label_field, (str, bytes)):
        labels = [str(x) for x in label_field]
        tokens = text.split()
        if len(tokens) == len(labels):
            spans = []
            for span_text, label in spans_from_bio(tokens, labels):
                if label in {"CAUSE", "EFFECT"}:
                    spans.append((span_text, label))
            return sorted(set(spans))
    return []


def exact_set_metrics(gold_items: Sequence[Tuple], pred_items: Sequence[Tuple]) -> Dict[str, float]:
    gold_set = set(gold_items)
    pred_set = set(pred_items)
    tp = len(gold_set & pred_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    precision = safe_float(tp, tp + fp)
    recall = safe_float(tp, tp + fn)
    f1 = f1_score(precision, recall)
    exact_match = 1.0 if gold_set == pred_set else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match": exact_match,
    }


def sequence_metrics(gold_tokens: Sequence[str], gold_labels: Sequence[str], pred_text: Any) -> Dict[str, Any]:
    pred_tokens, pred_labels = parse_token_label_pairs(pred_text)

    if pred_tokens and len(pred_tokens) == len(gold_tokens):
        aligned_pred_labels = pred_labels
    else:
        label_only = labels_only_from_output(pred_text)
        if len(label_only) >= len(gold_labels):
            aligned_pred_labels = label_only[: len(gold_labels)]
        else:
            aligned_pred_labels = label_only + ["O"] * max(0, len(gold_labels) - len(label_only))

    if len(aligned_pred_labels) < len(gold_labels):
        aligned_pred_labels += ["O"] * (len(gold_labels) - len(aligned_pred_labels))
    aligned_pred_labels = aligned_pred_labels[: len(gold_labels)]

    token_correct = sum(1 for g, p in zip(gold_labels, aligned_pred_labels) if str(g) == str(p))
    token_accuracy = safe_float(token_correct, len(gold_labels))

    gold_spans = set(spans_from_bio(gold_tokens, gold_labels))
    pred_spans = set(spans_from_bio(gold_tokens, aligned_pred_labels))
    span_stats = exact_set_metrics(sorted(gold_spans), sorted(pred_spans))

    tp = sum(1 for g, p in zip(gold_labels, aligned_pred_labels) if g == p and g != "O")
    fp = sum(1 for g, p in zip(gold_labels, aligned_pred_labels) if p != "O" and g != p)
    fn = sum(1 for g, p in zip(gold_labels, aligned_pred_labels) if g != "O" and g != p)
    precision = safe_float(tp, tp + fp)
    recall = safe_float(tp, tp + fn)
    token_f1 = f1_score(precision, recall)

    return {
        "token_accuracy": token_accuracy,
        "token_precision_non_o": precision,
        "token_recall_non_o": recall,
        "token_f1_non_o": token_f1,
        "span_precision": span_stats["precision"],
        "span_recall": span_stats["recall"],
        "span_f1": span_stats["f1"],
        "span_exact_match": span_stats["exact_match"],
        "gold_labels": list(gold_labels),
        "pred_labels": list(aligned_pred_labels),
        "gold_spans": sorted(gold_spans),
        "pred_spans": sorted(pred_spans),
    }


def evaluate_row(row: Dict[str, Any], prediction_text: str) -> Dict[str, Any]:
    task_type = CONFIG["task_type"]
    if task_type == "ner_entities":
        gold = get_gold_entity_pairs(row)
        pred = parse_entity_pairs(prediction_text, CONFIG["allowed_entity_labels"])
        metrics = exact_set_metrics(gold, pred)
        metrics.update({"gold": gold, "pred": pred})
        return metrics

    if task_type == "relation_triples":
        gold = get_gold_relation_triples(row)
        pred = parse_relation_triples(prediction_text)
        metrics = exact_set_metrics(gold, pred)
        metrics.update({"gold": gold, "pred": pred})
        return metrics

    if task_type == "binary_classification":
        gold = get_gold_binary_label(row)
        pred = parse_binary_label(prediction_text)
        positive = normalize_for_match(CONFIG["positive_label"])
        correct = 1.0 if gold == pred else 0.0
        return {
            "gold": gold,
            "pred": pred,
            "correct": correct,
            "tp": 1 if gold == positive and pred == positive else 0,
            "fp": 1 if gold != positive and pred == positive else 0,
            "fn": 1 if gold == positive and pred != positive else 0,
            "tn": 1 if gold != positive and pred != positive else 0,
        }

    if task_type == "causal_spans":
        gold = get_gold_causal_spans(row)
        pred_tokens, pred_labels = parse_token_label_pairs(prediction_text)
        if pred_tokens and pred_labels:
            pred = sorted(set((span, label) for span, label in spans_from_bio(pred_tokens, pred_labels) if label in {"CAUSE", "EFFECT"}))
        else:
            pred = parse_causal_span_lines(prediction_text)
        metrics = exact_set_metrics(gold, pred)
        metrics.update({"gold": gold, "pred": pred})
        return metrics

    if task_type == "sequence_labels":
        gold_tokens, gold_labels = get_gold_sequence(row)
        metrics = sequence_metrics(gold_tokens, gold_labels, prediction_text)
        metrics.update({"gold_tokens": gold_tokens})
        return metrics

    raise ValueError(f"Unsupported task type: {task_type}")


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    task_type = CONFIG["task_type"]
    summary: Dict[str, Any] = {
        "dataset_name": CONFIG["dataset_name"],
        "task_type": task_type,
        "num_examples": len(results),
    }

    if task_type in {"ner_entities", "relation_triples", "causal_spans"}:
        tp = sum(r["tp"] for r in results)
        fp = sum(r["fp"] for r in results)
        fn = sum(r["fn"] for r in results)
        precision = safe_float(tp, tp + fp)
        recall = safe_float(tp, tp + fn)
        summary.update({
            "precision": precision,
            "recall": recall,
            "f1": f1_score(precision, recall),
            "exact_match_rate": safe_float(sum(r["exact_match"] for r in results), len(results)),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        })
        return summary

    if task_type == "binary_classification":
        tp = sum(r["tp"] for r in results)
        fp = sum(r["fp"] for r in results)
        fn = sum(r["fn"] for r in results)
        tn = sum(r["tn"] for r in results)
        precision = safe_float(tp, tp + fp)
        recall = safe_float(tp, tp + fn)
        summary.update({
            "accuracy": safe_float(sum(r["correct"] for r in results), len(results)),
            "precision_positive": precision,
            "recall_positive": recall,
            "f1_positive": f1_score(precision, recall),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        })
        return summary

    if task_type == "sequence_labels":
        for key in (
            "token_accuracy",
            "token_precision_non_o",
            "token_recall_non_o",
            "token_f1_non_o",
            "span_precision",
            "span_recall",
            "span_f1",
            "span_exact_match",
        ):
            summary[key] = safe_float(sum(r[key] for r in results), len(results))
        return summary

    return summary


def build_output_row(example_index: int, row: Dict[str, Any], prompt: str, prediction_text: str, eval_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "example_index": example_index,
        "id": row.get("id", example_index),
        "text": get_text_column(row),
        "prompt": prompt,
        "prediction_text": prediction_text,
        "evaluation": eval_result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=CONFIG["default_model"])
    parser.add_argument("--split", default=None)
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--output-dir", type=str, default="outputs/eval_flare_causal20_sc_gpt5")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep between requests in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.jsonl"
    summary_path = output_dir / "summary.json"

    print(f"[load] Loading dataset {CONFIG['dataset_name']} ...")
    dataset_dict = load_dataset(CONFIG["dataset_name"])
    split = choose_split(dataset_dict, args.split or CONFIG["default_split"])
    dataset = dataset_dict[split]
    print(f"[load] Using split '{split}' with {len(dataset)} rows")

    end_index = len(dataset)
    if args.max_examples is not None:
        end_index = min(end_index, args.start_index + args.max_examples)

    client = OpenAI()
    results: List[Dict[str, Any]] = []

    with predictions_path.open("w", encoding="utf-8") as fout:
        for idx in range(args.start_index, end_index):
            row = dataset[idx]
            prompt = get_query(row)
            print(f"[eval] Example {idx}")
            prediction_text = call_model(client, args.model, prompt)
            eval_result = evaluate_row(row, prediction_text)
            results.append(eval_result)

            out_row = build_output_row(idx, row, prompt, prediction_text, eval_result)
            fout.write(json.dumps(out_row, ensure_ascii=False) + "\n")

            if args.sleep > 0:
                time.sleep(args.sleep)

    summary = summarize(results)
    summary["model"] = args.model
    summary["split"] = split
    summary["start_index"] = args.start_index
    summary["end_index_exclusive"] = end_index

    with summary_path.open("w", encoding="utf-8") as fout:
        json.dump(summary, fout, indent=2, ensure_ascii=False)

    print("[done] Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[done] Wrote predictions to {predictions_path}")
    print(f"[done] Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
