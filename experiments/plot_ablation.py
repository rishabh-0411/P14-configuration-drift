from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "ablation_precision_at_5.png"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

configurations = [
    "Baseline",
    "Full Risk Ranking",
    "Without Security Priority",
    "Without Availability Priority",
    "Equal Category Weights",
]

precision = [0.20, 0.80, 0.40, 0.60, 0.20]

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(configurations, precision)

ax.set_ylabel("Precision@5")
ax.set_xlabel("Configuration")
ax.set_title("Ablation Study: Precision@5")
ax.set_ylim(0, 1.0)
ax.tick_params(axis="x", labelrotation=20)

for bar, value in zip(bars, precision):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        value + 0.02,
        f"{value:.2f}",
        ha="center",
    )

fig.tight_layout()
fig.savefig(OUTPUT, dpi=300)
print(f"Plot saved to: {OUTPUT}")
plt.close(fig)
