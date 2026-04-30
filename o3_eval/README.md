# OpenFinLLM IE Evaluation — O3

Evaluate OpenAI **o3** on FLARE financial NLP benchmarks (information extraction tasks).

## Supported Datasets

| Dataset | Task | Samples |
|---------|------|---------|
| [flare-ner](https://huggingface.co/datasets/ChanceFocus/flare-ner) | Named Entity Recognition | 98 |
| [flare-finred](https://huggingface.co/datasets/ChanceFocus/flare-finred) | Relation Extraction | 1068 |
| [flare-causal20-sc](https://huggingface.co/datasets/ChanceFocus/flare-causal20-sc) | Sentence Classification | 8628 |
| [flare-cd](https://huggingface.co/datasets/ChanceFocus/flare-cd) | Causal Detection (Seq Label) | 226 |
| [flare-fnxl](https://huggingface.co/datasets/ChanceFocus/flare-fnxl) | Numeric Extreme Labelling | 318 |
| [flare-fsrl](https://huggingface.co/datasets/ChanceFocus/flare-fsrl) | Semantic Role Labelling | 97 |

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables:
```bash
export OPENAI_API_KEY="sk-..."
export HF_TOKEN="hf_..."          # optional, needed for gated datasets
```

## Usage

### Single dataset
```bash
python o3_flare_ner.py --dataset flare-ner --max-samples 20   # smoke test
python o3_flare_ner.py --dataset flare-ner                    # full eval
```

### All datasets (batch)
```bash
python run_all_flare.py --max-samples 20   # smoke test all
python run_all_flare.py                    # full eval all
```

### Key options
| Flag | Default | Description |
|------|---------|-------------|
| `--dataset` | `flare-ner` | Dataset alias or HuggingFace id |
| `--split` | `test` | Dataset split |
| `--max-samples` | `0` (all) | Limit samples for testing |
| `--max-retries` | `5` | API retry attempts per sample |
| `--backoff-seconds` | `2.0` | Base exponential backoff |
| `--request-delay` | `2.0` | Pause between API calls (rate-limit protection) |

## Output Files

Per dataset:
- `{slug}_o3_predictions.csv` — row_idx, text, gold_json, pred_json, success, error
- `{slug}_o3_metrics.json` — precision, recall, f1, total_samples, successful_samples

Batch summary:
- `flare_all_o3_summary.json`

## Resume Support

If interrupted, re-run the same command — already-successful samples are skipped automatically.
