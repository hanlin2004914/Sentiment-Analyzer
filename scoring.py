from collections import defaultdict


def score_prediction(predicted, expected):
    if not predicted or not expected:
        return 0.0

    if predicted.lower().strip() == expected.lower().strip():
        return 1.0

    # partial credit for adjacent sentiment labels
    order = ["negative", "neutral", "positive"]
    p = predicted.lower().strip()
    e = expected.lower().strip()

    if p in order and e in order:
        distance = abs(order.index(p) - order.index(e))
        if distance == 1:
            return 0.25

    return 0.0


def score_batch(predictions, expected_labels):
    scores = []
    for pred, gold in zip(predictions, expected_labels):
        scores.append(score_prediction(pred, gold))
    return scores


def accuracy(scores):
    if not scores:
        return 0.0
    perfect = sum(1 for s in scores if s == 1.0)
    return perfect / len(scores)


def breakdown_by_task(results):
    """
    Takes a list of dicts with 'task_type' and 'score' keys.
    Returns accuracy per task type.
    """
    groups = defaultdict(list)
    for r in results:
        groups[r["task_type"]].append(r["score"])

    breakdown = {}
    for task, scores in groups.items():
        perfect = sum(1 for s in scores if s == 1.0)
        breakdown[task] = {
            "accuracy": round(perfect / len(scores) * 100, 2),
            "total": len(scores),
            "correct": perfect
        }
    return breakdown


def breakdown_by_difficulty(results):
    """
    Takes a list of dicts with 'difficulty' and 'score' keys.
    Returns accuracy per difficulty level.
    """
    groups = defaultdict(list)
    for r in results:
        diff = r.get("difficulty", "unknown")
        groups[diff].append(r["score"])

    breakdown = {}
    for diff, scores in groups.items():
        perfect = sum(1 for s in scores if s == 1.0)
        breakdown[diff] = {
            "accuracy": round(perfect / len(scores) * 100, 2),
            "total": len(scores),
            "correct": perfect
        }
    return breakdown


if __name__ == "__main__":
    # quick test
    preds = ["positive", "negative", "neutral", "positive", "neutral"]
    golds = ["positive", "negative", "positive", "negative", "neutral"]

    scores = score_batch(preds, golds)
    print("Scores:", scores)
    print("Accuracy:", round(accuracy(scores) * 100, 1), "%")