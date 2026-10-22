
import json
import sys
from pathlib import Path

from detector.drift_detector import load_plan, detect_drift
from detector.risk_ranker import rank_drifts


def recommend_remediation(item):
    """Return a safe, reviewable recommendation for one drift item."""

    resource_type = item["resource_type"].lower()
    path = item["path"].lower()
    desired = item["after"]

    if resource_type == "kubernetes_role_v1" and "verbs" in path:
        return (
            f"Restore the RBAC verbs to {desired}. "
            "Review the permissions to ensure least privilege."
        )

    if resource_type == "kubernetes_service_v1" and "type" in path:
        return (
            f"Restore the Service type to {desired}. "
            "Verify whether external exposure is intended."
        )

    if "replicas" in path:
        return (
            f"Restore the deployment replica count to {desired}. "
            "Check pod readiness and application capacity afterward."
        )

    if "target_port" in path:
        return (
            f"Restore the Service target port to {desired}. "
            "Verify that the application listens on that port."
        )

    if "image" in path:
        return (
            f"Restore the declared container image to {desired}. "
            "Verify the image version and deployment health."
        )

    if "resources" in path and ("cpu" in path or "memory" in path):
        return (
            f"Restore the declared resource setting to {desired}. "
            "Check workload performance and resource usage afterward."
        )

    if resource_type == "kubernetes_config_map_v1" and "data." in path:
        return (
            f"Restore the declared configuration value to {desired}. "
            "Confirm that the application expects this value."
        )

    if "label" in path or "annotation" in path:
        return (
            f"Restore the declared label or annotation value to {desired}. "
            "Check whether any automation depends on the metadata."
        )

    return (
        f"Review this drift and restore the declared value {desired} "
        "if the change is not approved."
    )


def build_remediation_plan(ranked_items):
    """Create a prioritized remediation plan from ranked drift items."""

    plan_items = []

    for rank, item in enumerate(ranked_items, start=1):
        plan_items.append({
            "priority": rank,
            "resource": item["resource"],
            "resource_type": item["resource_type"],
            "attribute": item["path"],
            "category": item["category"],
            "severity": item["severity"],
            "risk_score": item["risk_score"],
            "live_value": item["before"],
            "desired_value": item["after"],
            "recommended_action": recommend_remediation(item),
            "execution_status": "recommendation_only",
        })

    return {
        "project": "P14 - Risk-Ranked Configuration Drift",
        "total_drift_items": len(plan_items),
        "severity_summary": {
            severity: sum(
                1 for item in plan_items
                if item["severity"] == severity
            )
            for severity in ("High", "Medium", "Low")
        },
        "automatic_changes_applied": False,
        "remediation_items": plan_items,
    }


def main():
    if len(sys.argv) not in (2, 3):
        print(
            "Usage: python detector\\remediation_planner.py "
            "<terraform_plan.json> [output.json]"
        )
        sys.exit(1)

    plan_path = Path(sys.argv[1])

    if not plan_path.exists():
        print(f"Error: Plan file not found: {plan_path}")
        sys.exit(1)

    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) == 3
        else Path("results") / "remediation_plan.json"
    )

    try:
        plan = load_plan(plan_path)
        drifts = detect_drift(plan)
        ranked_items = rank_drifts(drifts)
        remediation_plan = build_remediation_plan(ranked_items)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(remediation_plan, indent=2, default=str),
            encoding="utf-8",
        )

    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Error generating remediation plan: {error}")
        sys.exit(1)

    print("\n========================================")
    print("      P14 REMEDIATION PLAN")
    print("========================================\n")
    print(f"Drift items : {remediation_plan['total_drift_items']}")
    print(f"High risk   : {remediation_plan['severity_summary']['High']}")
    print(f"Medium risk : {remediation_plan['severity_summary']['Medium']}")
    print(f"Low risk    : {remediation_plan['severity_summary']['Low']}")
    print("Changes applied automatically: No")
    print(f"JSON report : {output_path.resolve()}\n")

    for item in remediation_plan["remediation_items"]:
        print(
            f"Priority #{item['priority']} | "
            f"{item['severity']} | "
            f"{item['category']} | "
            f"Score {item['risk_score']}"
        )
        print(f"Resource : {item['resource']}")
        print(f"Attribute: {item['attribute']}")
        print(f"Live     : {item['live_value']}")
        print(f"Desired  : {item['desired_value']}")
        print(f"Action   : {item['recommended_action']}")
        print("-" * 50)


if __name__ == "__main__":
    main()

