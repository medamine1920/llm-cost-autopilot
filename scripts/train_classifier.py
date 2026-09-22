"""Train the tier classifier and compare it against the rule-based router.

Run: python -m scripts.train_classifier

Evaluation:
  1. 5-fold cross-validation — every prompt is predicted by a model that never saw it
  2. Side-by-side comparison with rules v1 on the same prompts
  3. Misclassified prompts listed, so errors can be inspected
  4. Optional: held-out hand-written prompts (data/handwritten_v1.json), never used in training
"""

import json
from pathlib import Path
from statistics import mean, stdev

import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

from app.features import extract_features
from app.router import choose_tier

GOLDEN_PATH = Path("data/golden_v3.json")
LABELS_PATH = Path("data/labels_v3.json")
HANDWRITTEN_PATH = Path("data/handwritten_v1.json")
MODEL_PATH = Path("app/models/classifier.joblib")

CLOUD_THRESHOLD = 0.3   # route to cloud if P(moderate) > 0.3 — quality errors cost more than wasted cents


def load_dataset() -> tuple[list[str], list[int]]:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    prompts, y = [], []
    for item in golden:
        tier = labels.get(item["id"])
        if tier is None and item["check"] == "manual" and item["tier_label"] != "tbd":
            tier = item["tier_label"]                      # hand-labeled manual items
        if tier in ("simple", "moderate"):
            prompts.append(item["text"])
            y.append(1 if tier == "moderate" else 0)       # 1 = needs cloud
    return prompts, y


def build_model():
    return make_pipeline(
        DictVectorizer(),
        LogisticRegression(class_weight="balanced", max_iter=1000),
    )


def rules_predict(prompts: list[str]) -> list[int]:
    return [int(choose_tier(p)[0] == "moderate") for p in prompts]


def report(name: str, y_true: list[int], y_pred: list[int]) -> None:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    print(f"\n{name}: accuracy {accuracy_score(y_true, y_pred):.0%}  ({len(y_true)} prompts)")
    print(f"  sent to free model but needed cloud (quality risk): {fn}")
    print(f"  sent to cloud but free model was enough (wasted $):  {fp}")


def show_errors(name: str, prompts: list[str], y_true: list[int], y_pred: list[int]) -> None:
    errors = [(p, t) for p, t, pr in zip(prompts, y_true, y_pred) if t != pr]
    print(f"\nMisclassified by {name} ({len(errors)}):")
    for prompt, truth in errors:
        label = "moderate" if truth else "simple"
        print(f"  [true: {label:<8}] {prompt[:90]!r}")


def main() -> None:
    prompts, y = load_dataset()
    print(f"{len(y)} labeled prompts: {sum(y)} moderate, {len(y) - sum(y)} simple")

    X = [extract_features(p) for p in prompts]

    # --- 1. Cross-validated predictions for every prompt ---
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    proba = cross_val_predict(build_model(), X, y, cv=cv, method="predict_proba")[:, 1]
    y_clf = [int(p > CLOUD_THRESHOLD) for p in proba]
    y_rules = rules_predict(prompts)

    # per-fold accuracy, to see how stable the estimate is
    fold_acc = []
    for _, test_idx in cv.split(X, y):
        fold_acc.append(accuracy_score([y[i] for i in test_idx], [y_clf[i] for i in test_idx]))
    print(f"\nClassifier per-fold accuracy: {', '.join(f'{a:.0%}' for a in fold_acc)}"
          f"  → mean {mean(fold_acc):.0%} ± {stdev(fold_acc):.0%}")

    # --- 2. Side-by-side on the same prompts ---
    report("classifier (5-fold CV)", y, y_clf)
    report("rules v1", y, y_rules)

    # --- 3. Inspect the mistakes ---
    show_errors("classifier", prompts, y, y_clf)
    show_errors("rules v1", prompts, y, y_rules)

    # --- 4. Final model trained on all data ---
    model = build_model()
    model.fit(X, y)

    # --- 5. The real exam: hand-written prompts never seen in training ---
    if HANDWRITTEN_PATH.exists():
        hw = json.loads(HANDWRITTEN_PATH.read_text(encoding="utf-8"))
        hw = [item for item in hw if item["tier_label"] in ("simple", "moderate")]
        hw_prompts = [item["text"] for item in hw]
        hw_y = [1 if item["tier_label"] == "moderate" else 0 for item in hw]
        hw_proba = model.predict_proba([extract_features(p) for p in hw_prompts])[:, 1]

        print("\n=== Held-out hand-written prompts ===")
        report("classifier", hw_y, [int(p > CLOUD_THRESHOLD) for p in hw_proba])
        report("rules v1", hw_y, rules_predict(hw_prompts))
    else:
        print(f"\n(No {HANDWRITTEN_PATH} yet — the hand-written test is skipped.)")

    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()