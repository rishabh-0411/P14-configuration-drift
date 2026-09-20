import json
import sys
from pathlib import Path


def load_plan(plan_path):
    """Load a Terraform JSON plan."""
    with open(plan_path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def get_first_item(value):
    """Return the first item if Terraform represents a block as a list."""
    if isinstance(value, list) and value:
        return value[0]

    if isinstance(value, dict):
        return value

    return {}


def detect_drift(plan):
    """Extract resources that Terraform wants to change."""
    drifts = []

    for resource in plan.get("resource_changes", []):
        change = resource.get("change", {})
        actions = change.get("actions", [])

        if actions == ["no-op"]:
            continue

        drifts.append({
            "resource": resource.get("address"),
            "resource_type": resource.get("type"),
            "actions": actions,
            "before": change.get("before"),
            "after": change.get("after")
        })

    return drifts


def print_deployment_drift(drift):
    """Display useful information for Kubernetes deployment drift."""
    before = drift["before"] or {}
    after = drift["after"] or {}

    before_spec = get_first_item(before.get("spec"))
    after_spec = get_first_item(after.get("spec"))

    before_replicas = before_spec.get("replicas")
    after_replicas = after_spec.get("replicas")

    if before_replicas != after_replicas:
        print(f"Replicas : {before_replicas} -> {after_replicas}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python drift_detector.py <terraform_plan.json>")
        sys.exit(1)

    plan_path = Path(sys.argv[1])

    if not plan_path.exists():
        print(f"Error: File not found: {plan_path}")
        sys.exit(1)

    plan = load_plan(plan_path)
    drifts = detect_drift(plan)

    print("\n========================================")
    print("   P14 CONFIGURATION DRIFT DETECTOR")
    print("========================================\n")

    if not drifts:
        print("No configuration drift detected.")
        return

    print(f"Drifts detected: {len(drifts)}\n")

    for index, drift in enumerate(drifts, start=1):
        print(f"Drift #{index}")
        print("----------------------------------------")
        print(f"Resource : {drift['resource']}")
        print(f"Type     : {drift['resource_type']}")
        print(f"Action   : {', '.join(drift['actions'])}")

        if drift["resource_type"] == "kubernetes_deployment_v1":
            print_deployment_drift(drift)

        print("Status   : DRIFT DETECTED")
        print()


if __name__ == "__main__":
    main()