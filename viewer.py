from leaderboard import compute_rankings

def main():
    ranked = compute_rankings()

    print("\n===== MODEL LEADERBOARD =====\n")

    for _, row in ranked.iterrows():
        print(
            f"#{int(row['rank'])} | "
            f"{row['model']} | "
            f"F1: {row['f1']:.3f} | "
            f"Acc: {row['accuracy']:.3f} | "
            f"Latency: {row['latency']:.2f}s"
        )


if __name__ == "__main__":
    main()