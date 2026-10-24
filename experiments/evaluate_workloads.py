import csv
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "detector"))
sys.path.insert(0, str(ROOT / "experiments"))

from drift_detector import load_plan, detect_drift
from risk_ranker import rank_drifts
from evaluate_ranking import (
    load_labels,
    create_baseline_items,
    is_dangerous,
    precision_at_k,
    mean_rank_of_dangerous,
)


PROFILES = {
    "Security-focused": {"Security"},
    "Availability-cost-focused": {"Availability", "Cost"},
    "Mixed": {
        "Security", "Availability", "Cost", "Inconsequential"
    },
}

RANDOM_RUNS = 1000
BASE_SEED = 20261024


def category_of(item, labels):
    attribute = item.get("attribute", item.get("path", ""))
    return labels.get(attribute, {}).get("category", "Unknown")


def filter_profile(items, labels, categories):
    return [
        item for item in items
        if category_of(item, labels) in categories
    ]


def evaluate(ranking, labels):
    return {
        "precision_at_5": precision_at_k(ranking, labels, 5),
        "precision_at_10": precision_at_k(ranking, labels, 10),
        "mean_dangerous_rank": mean_rank_of_dangerous(ranking, labels),
    }


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python experiments/evaluate_workloads.py "
            "<terraform_plan.json> <drift_dataset.csv>"
        )
        sys.exit(1)

    plan_path = Path(sys.argv[1])
    dataset_path = Path(sys.argv[2])

    if not plan_path.exists() or not dataset_path.exists():
        print("Error: plan JSON or label CSV was not found.")
        sys.exit(1)

    plan = load_plan(plan_path)
    labels = load_labels(dataset_path)
    drifts = detect_drift(plan)

    baseline = create_baseline_items(drifts)
    proposed = rank_drifts(drifts)

    raw_results = []
    summary_results = []

    for profile_index, (profile_name, categories) in enumerate(
        PROFILES.items()
    ):
        baseline_profile = filter_profile(baseline, labels, categories)
        proposed_profile = filter_profile(proposed, labels, categories)

        if not baseline_profile:
            print(f"Skipping empty profile: {profile_name}")
            continue

        configurations = [
            ("Terraform baseline", baseline_profile),
            ("Proposed ranking", proposed_profile),
        ]

        print(f"\n{profile_name} (n={len(baseline_profile)})")

        for config_name, ranking in configurations:
            metrics = evaluate(ranking, labels)

            raw_results.append({
                "profile": profile_name,
                "configuration": config_name,
                "run": 1,
                **metrics,
            })

            summary_results.append({
                "profile": profile_name,
                "configuration": config_name,
                "n_items": len(ranking),
                "runs": 1,
                "precision_at_5_mean": metrics["precision_at_5"],
                "precision_at_5_sd": "",
                "precision_at_5_interval_low": "",
                "precision_at_5_interval_high": "",
                "precision_at_10_mean": metrics["precision_at_10"],
                "precision_at_10_sd": "",
                "precision_at_10_interval_low": "",
                "precision_at_10_interval_high": "",
                "mean_dangerous_rank_mean": (
                    metrics["mean_dangerous_rank"]
                    if metrics["mean_dangerous_rank"] is not None
                    else ""
                ),
                "mean_dangerous_rank_sd": "",
                "mean_dangerous_rank_interval_low": "",
                "mean_dangerous_rank_interval_high": "",
                "uncertainty_note": "Deterministic point estimate; no interval",
            })

        random_pools = {
            "precision_at_5": [],
            "precision_at_10": [],
            "mean_dangerous_rank": [],
        }

        rng = random.Random(BASE_SEED + profile_index)

        for run in range(1, RANDOM_RUNS + 1):
            random_ranking = list(baseline_profile)
            rng.shuffle(random_ranking)
            metrics = evaluate(random_ranking, labels)

            raw_results.append({
                "profile": profile_name,
                "configuration": "Random baseline",
                "run": run,
                **metrics,
            })

            for metric_name in random_pools:
                value = metrics[metric_name]
                if value is not None:
                    random_pools[metric_name].append(value)

        row = {
            "profile": profile_name,
            "configuration": "Random baseline",
            "n_items": len(baseline_profile),
            "runs": RANDOM_RUNS,
        }

        for metric_name, values in random_pools.items():
            mean_value = statistics.mean(values)
            sd_value = (
                statistics.stdev(values) if len(values) > 1 else 0.0
            )
            low = percentile(values, 0.025)
            high = percentile(values, 0.975)

            row[f"{metric_name}_mean"] = round(mean_value, 4)
            row[f"{metric_name}_sd"] = round(sd_value, 4)
            row[f"{metric_name}_interval_low"] = round(low, 4)
            row[f"{metric_name}_interval_high"] = round(high, 4)

        row["uncertainty_note"] = (
            "Empirical 2.5th-97.5th percentile of random permutations; "
            "not a confidence interval for generalization"
        )
        summary_results.append(row)

        print(
            "Random P@5: "
            f"mean={row['precision_at_5_mean']:.3f}, "
            f"SD={row['precision_at_5_sd']:.3f}, "
            f"95% permutation interval="
            f"[{row['precision_at_5_interval_low']:.3f}, "
            f"{row['precision_at_5_interval_high']:.3f}]"
        )

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    raw_path = results_dir / "workload_evaluation.csv"
    summary_path = results_dir / "workload_summary.csv"

    raw_fields = [
        "profile", "configuration", "run",
        "precision_at_5", "precision_at_10", "mean_dangerous_rank",
    ]

    summary_fields = [
        "profile", "configuration", "n_items", "runs",
        "precision_at_5_mean", "precision_at_5_sd",
        "precision_at_5_interval_low", "precision_at_5_interval_high",
        "precision_at_10_mean", "precision_at_10_sd",
        "precision_at_10_interval_low", "precision_at_10_interval_high",
        "mean_dangerous_rank_mean", "mean_dangerous_rank_sd",
        "mean_dangerous_rank_interval_low",
        "mean_dangerous_rank_interval_high", "uncertainty_note",
    ]

    with raw_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=raw_fields)
        writer.writeheader()
        writer.writerows(raw_results)

    with summary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_results)

    print("\nEvaluation completed.")
    print(f"Raw permutation results: {raw_path}")
    print(f"Summary results: {summary_path}")
    print(
        "\nCaution: profiles are subsets of one labelled corpus, "
        "not independent workloads. Random permutations measure "
        "ordering variability, not generalization uncertainty."
    )


if __name__ == "__main__":
    main()
