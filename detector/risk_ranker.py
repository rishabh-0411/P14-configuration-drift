import sys
from pathlib import Path

from detector.drift_detector import load_plan, detect_drift


def classify_risk(change, resource_type):
    """Classify an individual drift change."""

    path = change["path"].lower()
    resource = resource_type.lower()

    # -----------------------------
    # SECURITY
    # -----------------------------

    if resource == "kubernetes_service_v1" and "type" in path:
        return "Security", "High", 90

    if resource == "kubernetes_role_v1" and "verbs" in path:
        return "Security", "High", 90

    if (
        "role" in resource
        or "rolebinding" in resource
        or "permission" in path
        or "privilege" in path
    ):
        return "Security", "High", 90

    # -----------------------------
    # AVAILABILITY
    # -----------------------------

    if "replicas" in path:
        return "Availability", "High", 80

    if "target_port" in path:
        return "Availability", "High", 80

    if "port" in path:
        return "Availability", "High", 80

    if "image" in path:
        return "Availability", "Medium", 70

    # -----------------------------
    # COST
    # -----------------------------

    if "resources" in path and (
        "cpu" in path or "memory" in path
    ):
        return "Cost", "Medium", 60

    # -----------------------------
    # INCONSEQUENTIAL
    # -----------------------------

    if "label" in path or "annotation" in path:
        return "Inconsequential", "Low", 10

    if (
        resource == "kubernetes_config_map_v1"
        and "data." in path
    ):
        return "Inconsequential", "Low", 10

    # -----------------------------
    # UNKNOWN
    # -----------------------------

    return "Unknown", "Medium", 30


def rank_drifts(drifts):
    """Convert resource-level drift into individually ranked drift items."""

    ranked = []

    for drift in drifts:

        for change in drift["changes"]:

            category, severity, score = classify_risk(
                change,
                drift["resource_type"]
            )

            ranked.append({
                "resource": drift["resource"],
                "resource_type": drift["resource_type"],
                "path": change["path"],
                "before": change["before"],
                "after": change["after"],
                "category": category,
                "severity": severity,
                "risk_score": score,
            })

    ranked.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    return ranked


def main():

    if len(sys.argv) != 2:
        print("Usage: python risk_ranker.py <terraform_plan.json>")
        sys.exit(1)

    plan_path = Path(sys.argv[1])

    if not plan_path.exists():
        print(f"Error: File not found: {plan_path}")
        sys.exit(1)

    plan = load_plan(plan_path)

    drifts = detect_drift(plan)

    ranked = rank_drifts(drifts)

    print("\n========================================")
    print("   P14 INDIVIDUAL DRIFT RANKING")
    print("========================================\n")

    if not ranked:
        print("No configuration drift detected.")
        return

    print(f"Drift items detected: {len(ranked)}\n")

    for index, item in enumerate(ranked, start=1):

        print(f"Rank #{index}")
        print("----------------------------------------")
        print(f"Resource    : {item['resource']}")
        print(f"Attribute   : {item['path']}")
        print(f"Category    : {item['category']}")
        print(f"Severity    : {item['severity']}")
        print(f"Risk Score  : {item['risk_score']}")
        print(f"Live        : {item['before']}")
        print(f"Desired     : {item['after']}")
        print()


if __name__ == "__main__":
    main()
