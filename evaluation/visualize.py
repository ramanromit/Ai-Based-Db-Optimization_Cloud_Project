import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def generate_evaluation_plots(summary_csv: str = "evaluation/evaluation_summary.csv", output_dir: str = "evaluation/plots"):
    """Generates comparison plots from ablation evaluation summary data."""
    if not os.path.exists(summary_csv):
        print(f"Summary CSV {summary_csv} not found. Skipping plot generation.")
        return

    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(summary_csv)
    
    # Aggregated means per variant
    agg = df.groupby("variant").agg({
        "auth_p99_ms": ["mean", "std"],
        "auth_sla_compliance_pct": ["mean", "std"],
        "settle_p99_ms": ["mean", "std"],
        "analyt_p99_ms": ["mean", "std"],
        "throughput_qps": ["mean", "std"]
    })

    variants = ["baseline", "unconstrained", "constrained"]
    labels = ["Aurora Baseline\n(Agnostic)", "Unconstrained RL\n(Throughput-only)", "CAQI Constrained RL\n(Lagrangian SLA)"]
    colors = ["#e74c3c", "#f39c12", "#2ecc71"]

    # 1. Plot: Auth P99 Latency & SLA Threshold
    fig, ax = plt.subplots(figsize=(8, 5))
    means = [agg.loc[v, ("auth_p99_ms", "mean")] for v in variants]
    stds = [agg.loc[v, ("auth_p99_ms", "std")] for v in variants]
    
    bars = ax.bar(labels, means, yerr=stds, capsize=6, color=colors, alpha=0.85, edgecolor="black", width=0.55)
    ax.axhline(10.0, color="#c0392b", linestyle="--", linewidth=2.0, label="Auth SLA Budget (10ms)")
    
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1.0, f"{h:.1f} ms", ha="center", va="bottom", fontweight="bold", fontsize=11)

    ax.set_ylabel("Auth-Critical P99 Latency (ms)", fontsize=12)
    ax.set_title("Auth-Critical P99 Latency Under Load Spike (Lower is Better)", fontsize=13, fontweight="bold", pad=15)
    ax.set_ylim(0, max(means) * 1.3)
    ax.legend(loc="upper right", frameon=True, fontsize=11)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    auth_plot_path = os.path.join(output_dir, "auth_p99_comparison.png")
    plt.tight_layout()
    plt.savefig(auth_plot_path, dpi=300)
    plt.close()
    print(f"Generated plot: {auth_plot_path}")

    # 2. Plot: SLA Compliance Percentage
    fig, ax = plt.subplots(figsize=(8, 5))
    comp_means = [agg.loc[v, ("auth_sla_compliance_pct", "mean")] for v in variants]
    comp_stds = [agg.loc[v, ("auth_sla_compliance_pct", "std")] for v in variants]
    
    bars = ax.bar(labels, comp_means, yerr=comp_stds, capsize=6, color=colors, alpha=0.85, edgecolor="black", width=0.55)
    ax.axhline(99.0, color="#27ae60", linestyle="--", linewidth=1.5, label="Target SLA: 99.0%")
    
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1.5, f"{h:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=11)

    ax.set_ylabel("Auth SLA Compliance Rate (%)", fontsize=12)
    ax.set_title("Auth SLA Compliance Rate Across Load Spikes (Higher is Better)", fontsize=13, fontweight="bold", pad=15)
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right", frameon=True, fontsize=11)
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    comp_plot_path = os.path.join(output_dir, "sla_compliance_rate.png")
    plt.tight_layout()
    plt.savefig(comp_plot_path, dpi=300)
    plt.close()
    print(f"Generated plot: {comp_plot_path}")

if __name__ == "__main__":
    generate_evaluation_plots()

