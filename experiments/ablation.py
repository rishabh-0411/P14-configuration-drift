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
                "severity": row["severity"]
            }

    return labels


def normalize_changes(drift):
    """
    Group Kubernetes RBAC verb changes into
    one semantic drift item.
    """

    resource_type = drift["resource_type"]
    changes = drift["changes"]

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


def create_items(drifts):
    items = []

    for drift in drifts:

        changes = normalize_changes(drift)

        for change in changes:

            items.append({
                "resource": drift["resource"],
                "resource_type": drift["resource_type"],
                "attribute": change["path"],
                "before": change["before"],
                "after": change["after"]
            })

    return items


def is_dangerous(item, labels):

    label = labels.get(item["attribute"])

    if label is None:
        return False

    return label["severity"] in [
        "High",
        "Critical"
    ]


def precision_at_5(ranking, labels):

    top5 = ranking[:5]

    if not top5:
        return 0.0

    dangerous = sum(
        1
        for item in top5
        if is_dangerous(item, labels)
    )

    return dangerous / len(top5)


def score_category(category, attribute, weights):

    path = attribute.lower()

    # Match the actual risk_ranker.py behavior
    if category == "Availability" and "image" in path:
        return 70

    return weights.get(
        category,
        30
    )


def classify_category(attribute, resource_type):

    path = attribute.lower()
    resource = resource_type.lower()

    if (
        resource == "kubernetes_service_v1"
        and "type" in path
    ):
        return "Security"

    if (
        resource == "kubernetes_role_v1"
        and "verbs" in path
    ):
        return "Security"

    if (
        "role" in resource
        or "rolebinding" in resource
        or "permission" in path
        or "privilege" in path
    ):
        return "Security"

    if "replicas" in path:
        return "Availability"

    if "target_port" in path:
        return "Availability"

    if "port" in path:
        return "Availability"

    if "image" in path:
        return "Availability"

    if (
        "resources" in path
        and (
            "cpu" in path
            or "memory" in path
        )
    ):
        return "Cost"

    if (
        "label" in path
        or "annotation" in path
    ):
        return "Inconsequential"

    if (
        resource == "kubernetes_config_map_v1"
        and "data." in path
    ):
        return "Inconsequential"

    return "Unknown"


def rank_with_weights(items, weights):

    ranked = []

    for item in items:

        category = classify_category(
            item["attribute"],
            item["resource_type"]
        )

        score = score_category(
            category,
            item["attribute"],
            weights
        )

        ranked.append({
            **item,
            "category": category,
            "score": score
        })

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked


def main():

    if len(sys.argv) != 3:

        print(
            "Usage: python ablation.py "
            "<terraform_plan.json> <drift_dataset.csv>"
        )

        sys.exit(1)

    plan_path = Path(sys.argv[1])
    dataset_path = Path(sys.argv[2])

    plan = load_plan(plan_path)

    labels = load_labels(dataset_path)

    drifts = detect_drift(plan)

    items = create_items(drifts)

    # ------------------------------------------------
    # Baseline
    # ------------------------------------------------

    baseline = items

    # ------------------------------------------------
    # Full proposed model
    # ------------------------------------------------

    full_weights = {
        "Security": 90,
        "Availability": 80,
        "Cost": 60,
        "Inconsequential": 10
    }

    # ------------------------------------------------
    # Ablation 1:
    # Remove security priority
    # ------------------------------------------------

    no_security = {
        "Security": 60,
        "Availability": 80,
        "Cost": 60,
        "Inconsequential": 10
    }

    # ------------------------------------------------
    # Ablation 2:
    # Remove availability priority
    # ------------------------------------------------

    no_availability = {
        "Security": 90,
        "Availability": 60,
        "Cost": 60,
        "Inconsequential": 10
    }

    # ------------------------------------------------
    # Ablation 3:
    # Equal category weights
    # ------------------------------------------------

    equal_weights = {
        "Security": 60,
        "Availability": 60,
        "Cost": 60,
        "Inconsequential": 10
    }

    full_ranking = rank_with_weights(
        items,
        full_weights
    )

    no_security_ranking = rank_with_weights(
        items,
        no_security
    )

    no_availability_ranking = rank_with_weights(
        items,
        no_availability
    )

    equal_ranking = rank_with_weights(
        items,
        equal_weights
    )

    # ------------------------------------------------
    # Calculate results
    # ------------------------------------------------

    results = [
        (
            "Baseline",
            precision_at_5(
                baseline,
                labels
            )
        ),
        (
            "Full Risk Ranking",
            precision_at_5(
                full_ranking,
                labels
            )
        ),
        (
            "Without Security Priority",
            precision_at_5(
                no_security_ranking,
                labels
            )
        ),
        (
            "Without Availability Priority",
            precision_at_5(
                no_availability_ranking,
                labels
            )
        ),
        (
            "Equal Category Weights",
            precision_at_5(
                equal_ranking,
                labels
            )
        )
    ]

    # ------------------------------------------------
    # Print results
    # ------------------------------------------------

    print("\n========================================")
    print("          P14 ABLATION STUDY")
    print("========================================\n")

    print(
        "Configuration                  Precision@5"
    )

    print(
        "--------------------------------------------"
    )

    for name, value in results:

        print(
            f"{name:<30} {value:.2f}"
        )

    # ------------------------------------------------
    # Detailed rankings
    # ------------------------------------------------

    print("\n\nFull Risk Ranking:")
    print("----------------------------------------")

    for index, item in enumerate(
        full_ranking,
        start=1
    ):

        print(
            f"{index}. "
            f"{item['attribute']}"
            f" | {item['category']}"
            f" | Score: {item['score']}"
        )

    print("\n\nWithout Security Priority:")
    print("----------------------------------------")

    for index, item in enumerate(
        no_security_ranking,
        start=1
    ):

        print(
            f"{index}. "
            f"{item['attribute']}"
            f" | {item['category']}"
            f" | Score: {item['score']}"
        )

    print("\n\nWithout Availability Priority:")
    print("----------------------------------------")

    for index, item in enumerate(
        no_availability_ranking,
        start=1
    ):

        print(
            f"{index}. "
            f"{item['attribute']}"
            f" | {item['category']}"
            f" | Score: {item['score']}"
        )

    print("\n\nEqual Category Weights:")
    print("----------------------------------------")

    for index, item in enumerate(
        equal_ranking,
        start=1
    ):

        print(
            f"{index}. "
            f"{item['attribute']}"
            f" | {item['category']}"
            f" | Score: {item['score']}"
        )

    print(
        "\n========================================"
    )

    print("Ablation study completed successfully.")


if __name__ == "__main__":
    main()