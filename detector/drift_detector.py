import json
import sys
from pathlib import Path


def load_plan(plan_path):
    """Load Terraform JSON plan."""

    with open(
        plan_path,
        "r",
        encoding="utf-8-sig"
    ) as file:
        return json.load(file)


def get_changes(before, after, path=""):
    """
    Recursively compare Terraform before/after values.
    """

    changes = []

    if before == after:
        return changes

    # Dictionaries
    if isinstance(before, dict) and isinstance(after, dict):

        keys = set(before.keys()) | set(after.keys())

        for key in sorted(keys):

            current_path = (
                f"{path}.{key}"
                if path
                else key
            )

            old_value = before.get(key)
            new_value = after.get(key)

            changes.extend(
                get_changes(
                    old_value,
                    new_value,
                    current_path
                )
            )

        return changes

    # Lists
    if isinstance(before, list) and isinstance(after, list):

        max_length = max(
            len(before),
            len(after)
        )

        for index in range(max_length):

            old_value = (
                before[index]
                if index < len(before)
                else None
            )

            new_value = (
                after[index]
                if index < len(after)
                else None
            )

            current_path = (
                f"{path}[{index}]"
            )

            changes.extend(
                get_changes(
                    old_value,
                    new_value,
                    current_path
                )
            )

        return changes

    # Actual value difference
    changes.append({
        "path": path,
        "before": before,
        "after": after
    })

    return changes


def group_semantic_changes(resource_type, changes):
    """
    Convert low-level Terraform RBAC list changes
    into one meaningful permission drift.
    """

    if resource_type != "kubernetes_role_v1":
        return changes

    verb_changes = []
    other_changes = []

    for change in changes:

        path = change["path"]

        # Terraform produces paths such as:
        # rule[0].verbs[0]
        # rule[0].verbs[1]
        # rule[0].verbs[2]

        if (
            "verbs[" in path
            and path.startswith("rule[")
        ):
            verb_changes.append(change)

        else:
            other_changes.append(change)

    # If there are no RBAC verb changes,
    # return the original changes.
    if not verb_changes:
        return changes

    live_values = []

    desired_values = []

    for change in verb_changes:

        if change["before"] is not None:
            live_values.append(
                change["before"]
            )

        if change["after"] is not None:
            desired_values.append(
                change["after"]
            )

    # Sort so that the representation is
    # independent of Terraform's list ordering.
    live_values = sorted(
        live_values
    )

    desired_values = sorted(
        desired_values
    )

    other_changes.append({
        "path": "rule[0].verbs",
        "before": live_values,
        "after": desired_values
    })

    return other_changes


def detect_drift(plan):
    """
    Extract changed resources and their
    meaningful drift attributes.
    """

    drifts = []

    for resource in plan.get(
        "resource_changes",
        []
    ):

        change = resource.get(
            "change",
            {}
        )

        actions = change.get(
            "actions",
            []
        )

        if actions == ["no-op"]:
            continue

        before = change.get(
            "before"
        )

        after = change.get(
            "after"
        )

        resource_type = resource.get(
            "type"
        )

        attribute_changes = get_changes(
            before,
            after
        )

        attribute_changes = group_semantic_changes(
            resource_type,
            attribute_changes
        )

        drifts.append({
            "resource": resource.get(
                "address"
            ),
            "resource_type": resource_type,
            "actions": actions,
            "changes": attribute_changes
        })

    return drifts


def main():

    if len(sys.argv) != 2:

        print(
            "Usage: python drift_detector.py "
            "<terraform_plan.json>"
        )

        sys.exit(1)

    plan_path = Path(
        sys.argv[1]
    )

    if not plan_path.exists():

        print(
            f"Error: File not found: "
            f"{plan_path}"
        )

        sys.exit(1)

    plan = load_plan(
        plan_path
    )

    drifts = detect_drift(
        plan
    )

    print(
        "\n========================================"
    )

    print(
        "   P14 CONFIGURATION DRIFT DETECTOR"
    )

    print(
        "========================================\n"
    )

    if not drifts:

        print(
            "No configuration drift detected."
        )

        return

    print(
        f"Drifts detected: {len(drifts)}\n"
    )

    for index, drift in enumerate(
        drifts,
        start=1
    ):

        print(
            f"Drift #{index}"
        )

        print(
            "----------------------------------------"
        )

        print(
            f"Resource : {drift['resource']}"
        )

        print(
            f"Type     : {drift['resource_type']}"
        )

        print(
            f"Action   : {', '.join(drift['actions'])}"
        )

        if drift["changes"]:

            print("Changes:")

            for change in drift["changes"]:

                print(
                    f"  {change['path']}"
                )

                print(
                    f"    Live    : "
                    f"{change['before']}"
                )

                print(
                    f"    Desired : "
                    f"{change['after']}"
                )

        print(
            "Status   : DRIFT DETECTED"
        )

        print()


if __name__ == "__main__":
    main()