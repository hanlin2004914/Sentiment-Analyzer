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
