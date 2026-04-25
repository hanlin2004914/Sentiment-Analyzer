import os
import pandas as pd
from datetime import datetime

LEADERBOARD_PATH = "leaderboard.csv"


def log_run(model_name, accuracy, f1, latency, dataset="default"):
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model_name,
        "dataset": dataset,
        "accuracy": accuracy,
        "f1": f1,
        "latency": latency
    }

    if os.path.exists(LEADERBOARD_PATH):
        df = pd.read_csv(LEADERBOARD_PATH)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(LEADERBOARD_PATH, index=False)

    print("Logged run for:", model_name)