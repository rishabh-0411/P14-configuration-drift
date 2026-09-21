import matplotlib.pyplot as plt


metrics = [
    "Precision@5",
    "Precision@10"
]

baseline = [
    0.20,
    0.30
]

proposed = [
    0.80,
    0.40
]

x = range(len(metrics))

plt.figure(figsize=(8, 5))

plt.bar(
    [i - 0.2 for i in x],
    baseline,
    width=0.4,
    label="Baseline"
)

plt.bar(
    [i + 0.2 for i in x],
    proposed,
    width=0.4,
    label="Proposed Risk Ranking"
)

plt.xticks(
    list(x),
    metrics
)

plt.ylabel("Precision")
plt.xlabel("Metric")
plt.title(
    "Baseline vs Proposed Risk Ranking"
)

plt.ylim(0, 1.0)

plt.legend()

plt.tight_layout()

plt.savefig(
    "results/baseline_vs_proposed.png",
    dpi=300
)

plt.show()