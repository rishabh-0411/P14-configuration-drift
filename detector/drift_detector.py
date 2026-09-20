import json
import sys
from pathlib import Path


def load_plan(plan_path):
    """Load a Terraform JSON plan."""
    with open(plan_path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def get_changes(before, after, path=""):
    """
    Recursively compare Terraform's before and after values.
    Returns every detected difference.
    """

    changes = []

    if before == after:
        return changes

    # Dictionaries
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before.keys()) | set(after.keys())

        for key in sorted(keys):
            current_path = f"{path}.{key}" if path else key

            old_value = before.get(key)
            new_value = after.get(key)

            changes.extend(
                get_changes(old_value, new_value, current_path)
            )

        return changes

    # Lists
    if isinstance(before, list) and isinstance(after, list):
        max_length = max(len(before), len(after))

        for index in range(max_length):
            old_value = before[index] if index < len(before) else None
            new_value = after[index] if index < len(after) else None

            current_path = f"{path}[{index}]"

            changes.extend(
                get_changes(old_value, new_value, current_path)
            )

        return changes

    # Primitive values
    changes.append({
        "path": path,
        "before": before,
        "after": after
    })

    return changes


def detect_drift(plan):
    """Extract all changed resources from the Terraform plan."""

    drifts = []

    for resource in plan.get("resource_changes", []):

        change = resource.get("change", {})
        actions = change.get("actions", [])

        if actions == ["no-op"]:
            continue

        before = change.get("before")
        after = change.get("after")

        attribute_changes = get_changes(before, after)

        drifts.append({
            "resource": resource.get("address"),
            "resource_type": resource.get("type"),
            "actions": actions,
            "changes": attribute_changes
        })

    return drifts


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

        if drift["changes"]:

            print("Changes:")

            for change in drift["changes"]:

                print(f"  {change['path']}")
                print(f"    Live    : {change['before']}")
                print(f"    Desired : {change['after']}")

        print("Status   : DRIFT DETECTED")
        print()


if __name__ == "__main__":
    main()