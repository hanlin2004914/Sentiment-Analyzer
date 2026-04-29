"""
Basic tests for scoring and label normalization.
Run with: python tests.py
"""

from scoring import score_prediction, score_batch, accuracy
from normalize_labels import normalize_label


def test_exact_match():
    assert score_prediction("positive", "positive") == 1.0
    assert score_prediction("negative", "negative") == 1.0
    assert score_prediction("neutral", "neutral") == 1.0
    print("  test_exact_match passed")


def test_partial_credit():
    assert score_prediction("neutral", "positive") == 0.25
    assert score_prediction("neutral", "negative") == 0.25
    assert score_prediction("positive", "negative") == 0.0
    print("  test_partial_credit passed")


def test_wrong_prediction():
    assert score_prediction("positive", "negative") == 0.0
    assert score_prediction("negative", "positive") == 0.0
    print("  test_wrong_prediction passed")


def test_empty_inputs():
    assert score_prediction("", "positive") == 0.0
    assert score_prediction("positive", "") == 0.0
    assert score_prediction(None, "positive") == 0.0
    print("  test_empty_inputs passed")


def test_case_insensitive():
    assert score_prediction("POSITIVE", "positive") == 1.0
    assert score_prediction("Negative", "negative") == 1.0
    print("  test_case_insensitive passed")


def test_batch_scoring():
    preds = ["positive", "negative", "neutral"]
    golds = ["positive", "positive", "neutral"]
    scores = score_batch(preds, golds)
    assert scores == [1.0, 0.0, 1.0]
    print("  test_batch_scoring passed")


def test_accuracy():
    assert accuracy([1.0, 1.0, 0.0]) == 2 / 3
    assert accuracy([1.0, 1.0, 1.0]) == 1.0
    assert accuracy([0.0, 0.0, 0.0]) == 0.0
    assert accuracy([]) == 0.0
    print("  test_accuracy passed")


def test_normalize_direct():
    assert normalize_label("Positive") == "positive"
    assert normalize_label("NEGATIVE") == "negative"
    assert normalize_label("neutral.") == "neutral"
    assert normalize_label("bullish") == "positive"
    assert normalize_label("bearish") == "negative"
    print("  test_normalize_direct passed")


def test_normalize_letter():
    assert normalize_label("A") == "positive"
    assert normalize_label("B") == "neutral"
    assert normalize_label("C") == "negative"
    assert normalize_label("A. Positive") == "positive"
    print("  test_normalize_letter passed")


def test_normalize_verbose():
    assert normalize_label("The sentiment is bullish") == "positive"
    assert normalize_label("I think this is bearish overall") == "negative"
    print("  test_normalize_verbose passed")


def test_normalize_unknown():
    assert normalize_label("") == "unknown"
    assert normalize_label("asdfghjkl") == "unknown"
    print("  test_normalize_unknown passed")


if __name__ == "__main__":
    tests = [
        test_exact_match,
        test_partial_credit,
        test_wrong_prediction,
        test_empty_inputs,
        test_case_insensitive,
        test_batch_scoring,
        test_accuracy,
        test_normalize_direct,
        test_normalize_letter,
        test_normalize_verbose,
        test_normalize_unknown,
    ]

    print(f"Running {len(tests)} tests...\n")
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {test.__name__} - {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")