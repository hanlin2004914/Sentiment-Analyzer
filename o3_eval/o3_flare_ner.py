"""
Evaluate OpenAI o3 on FLARE financial NLP datasets.

Supported datasets:
    flare-ner, flare-finred, flare-causal20-sc, flare-cd, flare-fnxl, flare-fsrl

Usage:
    python o3_flare_ner.py --dataset flare-ner --max-samples 20
    python o3_flare_ner.py --dataset flare-finred
    python o3_flare_ner.py  # defaults to flare-ner, full test split

Outputs (in script directory):
    {dataset_slug}_o3_predictions.csv
    {dataset_slug}_o3_metrics.json
"""

import argparse
import ast
import csv
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import requests
from datasets import load_dataset
from openai import OpenAI

MODEL_NAME = "o3"
DEFAULT_DATASET = "flare-ner"
DATASET_SPLIT = "test"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_SECONDS = 2.0
DEFAULT_REQUEST_DELAY = 2.0
DEFAULT_TEXT_PREVIEW_LEN = 300

DATASET_ALIASES = {
    "flare-ner": "ChanceFocus/flare-ner",
    "flare-finred": "ChanceFocus/flare-finred",
    "flare-causal20-sc": "ChanceFocus/flare-causal20-sc",
    "flare-cd": "ChanceFocus/flare-cd",
    "flare-fnxl": "ChanceFocus/flare-fnxl",
    "flare-fsrl": "ChanceFocus/flare-fsrl",
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=str, default=DEFAULT_DATASET,
        help="Dataset alias or HuggingFace id (e.g. flare-ner, ChanceFocus/flare-cd)",
    )
    parser.add_argument("--split", type=str, default=DATASET_SPLIT)
    parser.add_argument(
        "--max-samples", type=int, default=int(os.getenv("MAX_SAMPLES", "0")),
        help="0 = all samples",
    )
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    parser.add_argument(
        "--request-delay", type=float,
        default=float(os.getenv("REQUEST_DELAY", str(DEFAULT_REQUEST_DELAY))),
        help="Seconds between API calls (rate-limit protection)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_env_secrets() -> Tuple[str, Optional[str]]:
    openai_key = (os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY") or "").strip()
    hf_token = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or "").strip()
    return openai_key, hf_token or None


def resolve_dataset_id(raw_name: str) -> str:
    name = (raw_name or "").strip()
    if name in DATASET_ALIASES:
        return DATASET_ALIASES[name]
    if "/" in name:
        return name
    return f"ChanceFocus/{name}"


def dataset_slug(dataset_id: str) -> str:
    return dataset_id.split("/")[-1].replace("-", "_")


def shorten_text(value: Any, max_len: int = DEFAULT_TEXT_PREVIEW_LEN) -> str:
    text = value if isinstance(value, str) else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 3]}..."


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(sample: Dict[str, Any], is_ner_task: bool) -> str:
    query = sample.get("query")
    text = sample.get("text", "")

    if is_ner_task:
        instruction = (
            "Return ONLY a JSON array of objects in this exact schema:\n"
            '[{"entity": "...", "type": "PER|ORG|LOC"}]\n'
            "No markdown, no explanation, no extra keys."
        )
    else:
        instruction = (
            "Return ONLY the final answer in the exact target format requested "
            "by the task. No explanation and no markdown."
        )

    if isinstance(query, str) and query.strip():
        return f"{query.strip()}\n\n{instruction}"

    return (
        f"Text:\n{text}\n\n{instruction}"
    )


# ---------------------------------------------------------------------------
# Parsing utilities
# ---------------------------------------------------------------------------

def try_parse_json_like(raw: Any) -> Any:
    if isinstance(raw, (list, dict)):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return []
    text = raw.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        return ast.literal_eval(text)
    except Exception:
        pass
    return []


def parse_flare_answer_string(raw: str) -> Set[Tuple[str, str]]:
    """Parse FLARE-NER answer format: 'entity, TYPE' per line."""
    entities: Set[Tuple[str, str]] = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        entity_part, type_part = line.rsplit(",", 1)
        entity = re.sub(r"\s+", " ", entity_part).strip()
        ent_type = type_part.strip().upper()
        if entity and ent_type in {"PER", "ORG", "LOC"}:
            entities.add((entity, ent_type))
    return entities


def extract_json_array_text(raw_output: str) -> str:
    text = raw_output.strip()
    if not text:
        return "[]"
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return text
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        return match.group(0).strip()
    return "[]"


def normalize_entities(payload: Any) -> Set[Tuple[str, str]]:
    items = payload if isinstance(payload, list) else []
    normalized: Set[Tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        entity = item.get("entity")
        ent_type = item.get("type")
        if not isinstance(entity, str) or not isinstance(ent_type, str):
            continue
        entity_clean = re.sub(r"\s+", " ", entity).strip()
        type_clean = ent_type.strip().upper()
        if not entity_clean or type_clean not in {"PER", "ORG", "LOC"}:
            continue
        normalized.add((entity_clean, type_clean))
    return normalized


def entities_to_json(entity_set: Set[Tuple[str, str]]) -> str:
    rows = [{"entity": e, "type": t} for (e, t) in sorted(entity_set)]
    return json.dumps(rows, ensure_ascii=False)


def parse_entities_from_json_string(value: Any) -> Set[Tuple[str, str]]:
    if isinstance(value, str):
        text = value.strip()
        parsed = try_parse_json_like(text)
        if isinstance(parsed, list):
            normalized = normalize_entities(parsed)
            if normalized:
                return normalized
        return parse_flare_answer_string(text)
    payload = try_parse_json_like(value)
    if isinstance(payload, list):
        return normalize_entities(payload)
    return set()


def normalize_text_items(value: Any) -> Set[str]:
    text = value if isinstance(value, str) else str(value or "")
    text = text.strip()
    if not text:
        return set()
    lines = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if clean:
            lines.append(clean)
    if not lines:
        clean = re.sub(r"\s+", " ", text).strip()
        return {clean} if clean else set()
    return set(lines)


def serialize_string_set(items: Set[str]) -> str:
    return json.dumps(sorted(items), ensure_ascii=False)


def deserialize_string_set(value: Any) -> Set[str]:
    parsed = try_parse_json_like(value)
    if isinstance(parsed, list):
        result: Set[str] = set()
        for item in parsed:
            clean = re.sub(r"\s+", " ", str(item)).strip()
            if clean:
                result.add(clean)
        if result:
            return result
    if isinstance(value, str):
        return normalize_text_items(value)
    return set()


# ---------------------------------------------------------------------------
# Model calling
# ---------------------------------------------------------------------------

def _extract_output_text(payload: dict) -> str:
    """Extract text from Responses API JSON (handles nested output structure)."""
    output_text = payload.get("output_text") or ""
    if not output_text:
        output_items = payload.get("output")
        if isinstance(output_items, list):
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    content = item.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "output_text":
                                output_text = block.get("text", "")
                                break
                if output_text:
                    break
    return str(output_text)


def call_model_with_retry(
    client: OpenAI,
    api_key: str,
    prompt: str,
    max_retries: int,
    base_backoff: float,
) -> Tuple[str, Optional[str]]:
    last_error: Optional[str] = None
    base_url = (os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL).rstrip("/")
    endpoint = f"{base_url}/responses"

    for attempt in range(max_retries):
        try:
            if hasattr(client, "responses"):
                response = client.responses.create(model=MODEL_NAME, input=prompt)
                output_text = response.output_text or ""
            else:
                response = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": MODEL_NAME, "input": prompt},
                    timeout=120,
                )
                if response.status_code >= 400:
                    detail = ""
                    try:
                        body = response.json()
                        if isinstance(body, dict):
                            err_obj = body.get("error")
                            if isinstance(err_obj, dict):
                                detail = str(err_obj.get("message") or body)
                            else:
                                detail = str(body)
                    except Exception:
                        detail = response.text or ""
                    if not detail:
                        detail = "<empty response body>"
                    raise RuntimeError(
                        f"HTTP {response.status_code} {response.reason}: {detail[:1000]}"
                    )
                payload = response.json()
                output_text = _extract_output_text(payload)
            return output_text, None
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            last_error = str(exc)
            if attempt == max_retries - 1:
                break
            sleep_seconds = base_backoff * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(sleep_seconds)

    return "", last_error or "Unknown model error"


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------

def load_existing_records(predictions_path: Path) -> Dict[int, Dict[str, Any]]:
    records: Dict[int, Dict[str, Any]] = {}
    if not predictions_path.exists():
        return records
    with predictions_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row_idx = int(row.get("row_idx", ""))
            except Exception:
                continue
            records[row_idx] = row
    return records


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    max_samples = args.max_samples if args.max_samples > 0 else None
    dataset_id = resolve_dataset_id(args.dataset)
    is_ner_task = "flare-ner" in dataset_id

    script_dir = Path(__file__).resolve().parent
    slug = dataset_slug(dataset_id)
    predictions_path = script_dir / f"{slug}_o3_predictions.csv"
    metrics_path = script_dir / f"{slug}_o3_metrics.json"

    api_key, hf_token = get_env_secrets()
    print(f"OPENAI_SET {bool(api_key)}")
    print(f"HF_SET {bool(hf_token)}")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY/API_KEY not set")

    client = OpenAI(api_key=api_key)

    dataset = load_dataset(dataset_id, split=args.split)
    total_available = len(dataset)
    target_total = min(max_samples, total_available) if max_samples else total_available

    existing_records = load_existing_records(predictions_path)
    already_done = {
        idx for idx, row in existing_records.items() if parse_bool(row.get("success"))
    }

    file_exists = predictions_path.exists()
    with predictions_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["row_idx", "text", "gold_json", "pred_json", "success", "error"],
        )
        if not file_exists:
            writer.writeheader()

        try:
            for idx in range(target_total):
                if idx in already_done:
                    continue

                if args.request_delay > 0:
                    time.sleep(args.request_delay)

                sample = dataset[idx]
                text_preview = shorten_text(sample.get("text", ""))
                prompt = build_prompt(sample, is_ner_task=is_ner_task)

                if is_ner_task:
                    gold_items = {
                        f"{entity}|||{ent_type}"
                        for entity, ent_type in parse_entities_from_json_string(
                            sample.get("answer", "[]")
                        )
                    }
                    gold_json = entities_to_json(
                        {tuple(item.split("|||", 1)) for item in gold_items if "|||" in item}
                    )
                else:
                    gold_items = normalize_text_items(sample.get("answer", ""))
                    gold_json = serialize_string_set(gold_items)

                output_text, error = call_model_with_retry(
                    client=client,
                    api_key=api_key,
                    prompt=prompt,
                    max_retries=args.max_retries,
                    base_backoff=args.backoff_seconds,
                )

                pred_items: Set[str] = set()
                success = False

                if not error:
                    if is_ner_task:
                        json_array_text = extract_json_array_text(output_text)
                        pred_payload = try_parse_json_like(json_array_text)
                        pred_items = {
                            f"{entity}|||{ent_type}"
                            for entity, ent_type in normalize_entities(pred_payload)
                        }
                    else:
                        pred_items = normalize_text_items(output_text)
                    success = True

                row = {
                    "row_idx": idx,
                    "text": text_preview,
                    "gold_json": gold_json,
                    "pred_json": (
                        entities_to_json(
                            {tuple(item.split("|||", 1)) for item in pred_items if "|||" in item}
                        )
                        if is_ner_task
                        else serialize_string_set(pred_items)
                    ),
                    "success": success,
                    "error": error or "",
                }
                writer.writerow(row)
                existing_records[idx] = row
                f.flush()
                print(f"Processed sample {idx + 1}/{target_total} (success={success})")
        except KeyboardInterrupt:
            print("\n[Interrupted] Progress saved. Re-run to resume.")

    # Compute metrics
    tp = 0
    fp = 0
    fn = 0
    successful_samples = 0

    for idx in range(target_total):
        row = existing_records.get(idx)
        if not row:
            continue

        if is_ner_task:
            gold_set = {
                f"{entity}|||{ent_type}"
                for entity, ent_type in parse_entities_from_json_string(row.get("gold_json", "[]"))
            }
            pred_set = {
                f"{entity}|||{ent_type}"
                for entity, ent_type in parse_entities_from_json_string(row.get("pred_json", "[]"))
            }
        else:
            gold_set = deserialize_string_set(row.get("gold_json", "[]"))
            pred_set = deserialize_string_set(row.get("pred_json", "[]"))
        if parse_bool(row.get("success")):
            successful_samples += 1

        tp += len(gold_set & pred_set)
        fp += len(pred_set - gold_set)
        fn += len(gold_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    metrics = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "total_samples": target_total,
        "successful_samples": successful_samples,
    }
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"Saved predictions to: {predictions_path}")
    print(f"Saved metrics to: {metrics_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
