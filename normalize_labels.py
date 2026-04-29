import re

SENTIMENT_MAP = {
    "positive": "positive",
    "pos": "positive",
    "bullish": "positive",
    "buy": "positive",
    "negative": "negative",
    "neg": "negative",
    "bearish": "negative",
    "sell": "negative",
    "neutral": "neutral",
    "mixed": "neutral",
    "hold": "neutral",
}

def normalize_label(raw_output):
    if not raw_output:
        return "unknown"

    cleaned = raw_output.strip().lower().rstrip(".")

    # direct match
    if cleaned in SENTIMENT_MAP:
        return SENTIMENT_MAP[cleaned]

    # check for letter answers like "A" or "A. Positive"
    letter_match = re.match(r"^\(?([a-c])\)?\.?\s*(.*)?$", cleaned)
    if letter_match:
        letter = letter_match.group(1)
        defaults = {"a": "positive", "b": "neutral", "c": "negative"}
        return defaults.get(letter, "unknown")

    # try to find a label buried in a longer response
    for keyword, label in SENTIMENT_MAP.items():
        if keyword in cleaned:
            return label

    return "unknown"

def normalize_batch(responses):
    return [normalize_label(r) for r in responses]

if __name__ == "__main__":
    test_cases = [
        "Positive",
        "NEGATIVE",
        "A. Positive",
        "B",
        "The sentiment is bullish",
        "neutral.",
        "I think this is bearish overall",
        "",
        "not sure what to say",
    ]
    for tc in test_cases:
        result = normalize_label(tc)
        print(f"  '{tc}' -> {result}")