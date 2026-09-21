import matplotlib.pyplot as plt


configurations = [
    "Baseline",
    "Full Risk Ranking",
    "Without Security Priority",
    "Without Availability Priority",
    "Equal Category Weights"
]

precision = [
    0.20,
    0.80,
    0.40,
    0.60,
    0.20
]

plt.figure(figsize=(10, 6))

bars = plt.bar(
    configurations,
    precision
)

plt.ylabel("Precision@5")
plt.xlabel("Configuration")
plt.title("Ablation Study: Precision@5")

plt.ylim(0, 1.0)

plt.xticks(
    rotation=20,
    ha="right"
)

for bar, value in zip(bars, precision):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        value + 0.02,
        f"{value:.2f}",
        ha="center"
    )

plt.tight_layout()

plt.savefig(
    "results/ablation_precision_at_5.png",
    dpi=300
)

plt.show()