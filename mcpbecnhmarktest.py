import requests
import time
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"


def get_articles(n=5):
    res = requests.post(
        "http://127.0.0.1:8000/tools/get_wsj_titles",
        json={"limit": n}
    )

    return res.json().get("titles", [])


def build_prompt(text):
    return f"""
Classify sentiment.

Text: {text}

Return JSON:
{{"label":"negative|neutral|positive"}}
"""


def call_model(text):
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": build_prompt(text),
            "stream": False
        }
    )

    try:
        return json.loads(res.json()["response"])["label"]
    except:
        return "UNKNOWN"


def main():
    titles = get_articles(10)

    print("\nRunning Benchmark...\n")

    for t in titles:
        start = time.time()
        pred = call_model(t)
        latency = time.time() - start

        print(f"{pred.upper():<10} | {latency:.2f}s | {t}")


if __name__ == "__main__":
    main()