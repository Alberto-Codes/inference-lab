# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["matplotlib==3.10.7"]
# ///
"""Render a standalone saturation figure from the saved aggregate report."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    """Plot repetition ranges without treating repeated documents as independent."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.input.read_text())
    rows = sorted(
        (r for r in report["ranges"] if r["cache"] == "repeated"),
        key=lambda r: r["rate"],
    )
    x = [r["rate"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for key, label, color in [
        ("completed_per_s_during_arrivals", "During arrivals", "#00796b"),
        ("completed_per_s_including_drain", "Including drain", "#b35b00"),
    ]:
        means = [r[key]["mean"] for r in rows]
        errors = [
            [r[key]["mean"] - r[key]["min"] for r in rows],
            [r[key]["max"] - r[key]["mean"] for r in rows],
        ]
        axes[0].errorbar(
            x, means, yerr=errors, marker="o", capsize=4, label=label, color=color
        )
    axes[0].plot(
        x, x, linestyle="--", color="#777777", linewidth=1, label="Offered = completed"
    )
    axes[0].set(
        ylabel="Nonempty, stop-terminated pages/s", title="Completed throughput"
    )
    key = "all_e2e_p95_s"
    axes[1].errorbar(
        x,
        [r[key]["mean"] for r in rows],
        yerr=[
            [r[key]["mean"] - r[key]["min"] for r in rows],
            [r[key]["max"] - r[key]["mean"] for r in rows],
        ],
        marker="s",
        capsize=4,
        color="#496c9b",
    )
    axes[1].set(
        ylabel="All-outcome p95 latency (seconds)",
        title="Queueing included; rejections included",
    )
    for axis in axes:
        axis.set_xlabel("Offered pages/s")
        axis.set_xticks(x)
        axis.set_ylim(bottom=0)
        axis.grid(alpha=0.2)
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "RTX 4090 · repeated CORD inputs · mean and min-max across repetitions"
    )
    with args.output.open("xb") as output:
        fig.savefig(
            output, format=args.output.suffix.lstrip("."), metadata={"Date": None}
        )
    plt.close(fig)
    print(json.dumps({"status": "rendered", "output": str(args.output)}))


if __name__ == "__main__":
    main()
