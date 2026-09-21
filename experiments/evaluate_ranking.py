import csv
import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1] / "detector")
)

from drift_detector import load_plan, detect_drift
from risk_ranker import rank_drifts


def load_labels(csv_path):
    labels = {}

    with open(csv_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            labels[row["attribute"]] = {
                "category": row["category"],
                "severity": row["severity"],
            }

    return labels


def normalize_changes(drift):
    """
    Convert low-level Terraform changes into
    semantic drift items for fair evaluation.
    """

    resource_type = drift["resource_type"]
    changes = drift["changes"]

    # Group Kubernetes RBAC verb changes
    if resource_type == "kubernetes_role_v1":

        verb_changes = [
            change
            for change in changes
            if "verbs[" in change["path"]
        ]

        other_changes = [
            change
            for change in changes
            if "verbs[" not in change["path"]
        ]

        normalized = []
        normalized.extend(other_changes)

        if verb_changes:
            live_values = [
                change["before"]
                for change in verb_changes
                if change["before"] is not None
            ]

            desired_values = [
                change["after"]
                for change in verb_changes
                if change["after"] is not None
            ]

            normalized.append({
                "path": "rule[0].verbs",
                "before": sorted(live_values),
                "after": sorted(desired_values)
            })

        return normalized

    return changes


def create_baseline_items(drifts):
    """
    Create the unranked Terraform ordering.

    Both baseline and proposed methods operate on
    the same semantic drift items.
    """

    items = []

    for drift in drifts:

        semantic_changes = normalize_changes(drift)

        for change in semantic_changes:

            items.append({
                "resource": drift["resource"],
                "resource_type": drift["resource_type"],
                "attribute": change["path"],
                "before": change["before"],
                "after": change["after"],
            })

    return items


def get_attribute(item):
    return item.get(
        "attribute",
        item.get("path")
    )


def is_dangerous(item, labels):
    attribute = get_attribute(item)

    label = labels.get(attribute)

    if label is None:
        return False

    return label["severity"] in [
        "High",
        "Critical"
    ]


def precision_at_k(ranking, labels, k):

    if not ranking:
        return 0.0

    top_k = ranking[:k]

    relevant = sum(
        1
        for item in top_k
        if is_dangerous(item, labels)
    )

    return relevant / len(top_k)


def mean_rank_of_dangerous(ranking, labels):

    ranks = []

    for index, item in enumerate(
        ranking,
        start=1
    ):

        if is_dangerous(item, labels):
            ranks.append(index)

    if not ranks:
        return None

    return sum(ranks) / len(ranks)


def main():

    if len(sys.argv) != 3:
        print(
            "Usage: python evaluate_ranking.py "
            "<terraform_plan.json> <drift_dataset.csv>"
        )
        sys.exit(1)

    plan_path = Path(sys.argv[1])
    dataset_path = Path(sys.argv[2])

    if not plan_path.exists():
        print(
            f"Error: Plan file not found: "
            f"{plan_path}"
        )
        sys.exit(1)

    if not dataset_path.exists():
        print(
            f"Error: Dataset file not found: "
            f"{dataset_path}"
        )
        sys.exit(1)

    plan = load_plan(plan_path)

    labels = load_labels(dataset_path)

    drifts = detect_drift(plan)

    # -----------------------------
    # BASELINE
    # -----------------------------

    baseline = create_baseline_items(drifts)

    baseline_precision_5 = precision_at_k(
        baseline,
        labels,
        5
    )

    baseline_precision_10 = precision_at_k(
        baseline,
        labels,
        10
    )

    baseline_mean_rank = (
        mean_rank_of_dangerous(
            baseline,
            labels
        )
    )

    # -----------------------------
    # PROPOSED
    # -----------------------------

    proposed = rank_drifts(drifts)

    proposed_precision_5 = precision_at_k(
        proposed,
        labels,
        5
    )

    proposed_precision_10 = precision_at_k(
        proposed,
        labels,
        10
    )

    proposed_mean_rank = (
        mean_rank_of_dangerous(
            proposed,
            labels
        )
    )

    # -----------------------------
    # RESULTS
    # -----------------------------

    print("\n========================================")
    print("       P14 RANKING EVALUATION")
    print("========================================\n")

    print(
        f"Total semantic drift items: "
        f"{len(baseline)}"
    )

    dangerous_count = sum(
        1
        for item in baseline
        if is_dangerous(item, labels)
    )

    print(
        f"Dangerous drift items      : "
        f"{dangerous_count}"
    )

    print(
        "\nMetric                 Baseline      Proposed"
    )

    print(
        "------------------------------------------------"
    )

    print(
        f"Precision@5            "
        f"{baseline_precision_5:.2f}          "
        f"{proposed_precision_5:.2f}"
    )

    print(
        f"Precision@10           "
        f"{baseline_precision_10:.2f}          "
        f"{proposed_precision_10:.2f}"
    )

    baseline_rank_text = (
        f"{baseline_mean_rank:.2f}"
        if baseline_mean_rank is not None
        else "N/A"
    )

    proposed_rank_text = (
        f"{proposed_mean_rank:.2f}"
        if proposed_mean_rank is not None
        else "N/A"
    )

    print(
        f"Mean dangerous rank    "
        f"{baseline_rank_text:<13}"
        f"{proposed_rank_text}"
    )

    # -----------------------------
    # BASELINE ORDER
    # -----------------------------

    print("\nBaseline ordering:")
    print("----------------------------------------")

    for i, item in enumerate(
        baseline,
        start=1
    ):

        attribute = get_attribute(item)

        label = labels.get(
            attribute,
            {}
        )

        category = label.get(
            "category",
            "Unknown"
        )

        severity = label.get(
            "severity",
            "Unknown"
        )

        print(
            f"{i}. {attribute}"
            f" | Category: {category}"
            f" | Severity: {severity}"
        )

    # -----------------------------
    # PROPOSED ORDER
    # -----------------------------

    print("\nProposed ordering:")
    print("----------------------------------------")

    for i, item in enumerate(
        proposed,
        start=1
    ):

        print(
            f"{i}. {item['path']}"
            f" | Category: {item['category']}"
            f" | Severity: {item['severity']}"
            f" | Risk Score: {item['risk_score']}"
        )

    # -----------------------------
    # SUMMARY
    # -----------------------------

    print("\n========================================")
    print("              SUMMARY")
    print("========================================")

    print(
        f"Baseline Precision@5 : "
        f"{baseline_precision_5:.2f}"
    )

    print(
        f"Proposed Precision@5 : "
        f"{proposed_precision_5:.2f}"
    )

    print(
        f"Baseline Precision@10: "
        f"{baseline_precision_10:.2f}"
    )

    print(
        f"Proposed Precision@10: "
        f"{proposed_precision_10:.2f}"
    )

    print(
        f"Baseline Mean Rank   : "
        f"{baseline_rank_text}"
    )

    print(
        f"Proposed Mean Rank   : "
        f"{proposed_rank_text}"
    )

    print(
        "\nEvaluation completed successfully."
    )


if __name__ == "__main__":
    main()