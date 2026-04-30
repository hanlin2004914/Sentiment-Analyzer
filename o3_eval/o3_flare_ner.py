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
