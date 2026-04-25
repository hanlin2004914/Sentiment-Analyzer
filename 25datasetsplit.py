import random
import json
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score


# -------------------------
# CONFIG
# -------------------------

SPLIT_RATIO = 0.75
LABEL_COL = "label"
TEXT_COL = "text"
RANDOM_SEED = 42


# -------------------------
# DATA LOADING
# -------------------------

def load_dataset(path):
    if path.endswith(".csv"):
        df = pd.read_csv(path)
        return df.to_dict("records")

    elif path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    else:
        raise ValueError("Only CSV and JSON supported")


# -------------------------
# SPLIT
# -------------------------

def split_dataset(data, ratio=0.75):
    random.seed(RANDOM_SEED)
    random.shuffle(data)

    split_idx = int(len(data) * ratio)

    train = data[:split_idx]
    test = data[split_idx:]

    return train, test


# -------------------------
# MODEL INTERFACE (EDIT THIS)
# -------------------------

def train_model(train_data):
    """
    Replace this with real training logic if needed.
    For LLMs, this might just store examples for few-shot.
    """
    return train_data


def predict(model, text):
    """
    Replace this with your model call.
    Must return one of the labels.
    """

    # ---- EXAMPLE PLACEHOLDER ----
    # random guess baseline
    return random.choice(["negative", "neutral", "positive"])


# -------------------------
# EVALUATION
# -------------------------

def evaluate(model, test_data):
    y_true = []
    y_pred = []

    for row in test_data:
        text = row[TEXT_COL]
        label = row[LABEL_COL]

        pred = predict(model, text)

        if pred is None:
            continue

        y_true.append(label)
        y_pred.append(pred)

    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro")

    return acc, f1


# -------------------------
# MAIN
# -------------------------

def run(path):
    print("Loading dataset...")
    data = load_dataset(path)

    print("Total samples:", len(data))

    print("\nSplitting dataset (75/25)...")
    train_data, test_data = split_dataset(data, SPLIT_RATIO)

    print("Train size:", len(train_data))
    print("Test size:", len(test_data))

    print("\nTraining model...")
    model = train_model(train_data)

    print("\nEvaluating model...")
    acc, f1 = evaluate(model, test_data)

    print("\n===== RESULTS =====")
    print("Accuracy:", round(acc, 4))
    print("Macro F1:", round(f1, 4))


# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":
    # change this to your dataset
    run("dataset.csv")