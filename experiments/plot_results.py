from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "baseline_vs_proposed.png"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

metrics = ["Precision@5", "Precision@10"]
baseline = [0.20, 0.30]
proposed = [0.80, 0.40]

x = range(len(metrics))

fig, ax = plt.subplots(figsize=(8, 5))
ax.bar([i - 0.2 for i in x], baseline, width=0.4, label="Baseline")
ax.bar([i + 0.2 for i in x], proposed, width=0.4,
       label="Proposed Risk Ranking")

ax.set_xticks(list(x), metrics)
ax.set_ylabel("Precision")
ax.set_xlabel("Metric")
ax.set_title("Baseline vs Proposed Risk Ranking")
ax.set_ylim(0, 1.0)
ax.legend()

fig.tight_layout()
fig.savefig(OUTPUT, dpi=300)
print(f"Plot saved to: {OUTPUT}")
plt.close(fig)
