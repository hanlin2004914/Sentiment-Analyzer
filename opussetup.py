import json
from anthropic import Anthropic

client = Anthropic()


def predict_opus(text, model_name):
    prompt = f"""
Classify sentiment.

Text: {text}

Return JSON:
{{"label":"negative|neutral|positive"}}
"""

    res = client.messages.create(
        model=model_name,
        max_tokens=50,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(res.content[0].text)["label"]
    except:
        return "UNKNOWN"