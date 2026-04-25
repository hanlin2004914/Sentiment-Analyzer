import pandas as pd

LEADERBOARD_PATH = "leaderboard.csv"


def load_leaderboard():
    return pd.read_csv(LEADERBOARD_PATH)


def compute_rankings():
    df = load_leaderboard()

    # group by model
    grouped = df.groupby("model").agg({
        "accuracy": "mean",
        "f1": "mean",
        "latency": "mean"
    }).reset_index()

    # sort by F1 (primary), then accuracy
    ranked = grouped.sort_values(
        by=["f1", "accuracy"],
        ascending=False
    )

    ranked["rank"] = range(1, len(ranked) + 1)

    return ranked


def best_model():
    ranked = compute_rankings()
    return ranked.iloc[0]