import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"


def predict_ollama(text, model_name):
    prompt = f"""
Classify sentiment.

Text: {text}

Return JSON:
{{"label":"negative|neutral|positive"}}
"""

    res = requests.post(
        OLLAMA_URL,
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
    )

    try:
        return json.loads(res.json()["response"])["label"]
    except:
        return "UNKNOWN"