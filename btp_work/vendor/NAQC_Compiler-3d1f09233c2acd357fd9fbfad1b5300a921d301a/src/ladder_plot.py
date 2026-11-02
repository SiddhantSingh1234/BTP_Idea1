import argparse
import glob
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

LADDER_ORDER = [
    "1_all_random",
    "2_greedy_nearest_idle_parking",
    "3_hungarian",
    "4_CoM_subset",
    "5_rft_idle_parking",
    "6_dynamic_slot_0q_move",
    "7_dynamic_slot_01q_move",
    "8_optimized_eviction",
    # "9_rft_hungarian_bias",
]

def pretty_name(variant: str) -> str:
    """Convert variant names to display names."""
    name_mapping = {
        "4_CoM_subset": "Method A",
        "8_optimized_eviction": "Method B",
        "DasAtom": "DasAtom",
    }
    return name_mapping.get(variant, variant)

FEATURES_TO_PLOT = [
    "Num CZ Gates",
    "Circuit Depth",
    "Fidelity (DasAtom Model)",
    "Fidelity (Realistic)",
    "Movement Fidelity",
    "Num Movement Ops",
    "Num Transferred Qubits",
    "Num Moves",
    "Total Move Distance",
    "Num Partitions",
    "Num Gate Cycles",
    "Elapsed Time (s)",
    "Total_T (us)",
    "Idle Time (us)",
]


def naturalize_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().str.replace(
        r"\d+", lambda m: f"{int(m.group()):08d}", regex=True
    )


def load_ladder_csvs(dataset: str, csv_dir: str) -> Dict[str, pd.DataFrame]:
    pattern = os.path.join(csv_dir, f"{dataset}_ladder_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No ladder CSVs found matching: {pattern}")

    out: Dict[str, pd.DataFrame] = {}
    for fp in files:
        base = os.path.basename(fp)
        # {dataset}_ladder_{variant}.csv
        variant = base[len(f"{dataset}_ladder_") : -len(".csv")]
        df = pd.read_csv(fp)
        out[variant] = df
    
    # Try to load DasAtom data
    if dataset == 'tetris':
        dasatom_csv = os.path.join('results/qtetris_compiled_csv', f"qtetris_dasatom_1.2x.csv")
        dasatom_sqrt_csv = os.path.join('results/qtetris_compiled_csv', f"qtetris_dasatom.csv")
    else:
        dasatom_csv = os.path.join('results/qft_step5_ladder_rint2', f"dasatom_qft_step5_1.2x_results.csv")
        dasatom_sqrt_csv = os.path.join('results/qft_step5_ladder_rint2', f"dasatom_qft_step5_results.csv")

    if os.path.exists(dasatom_csv):
        try:
            dasatom_df = pd.read_csv(dasatom_csv)
            out["DasAtom (1.2x)"] = dasatom_df
            print(f"Loaded DasAtom (1.2x) data from: {dasatom_csv}")
        except Exception as e:
            print(f"Warning: Failed to load DasAtom (1.2x) CSV {dasatom_csv}: {e}")

    if os.path.exists(dasatom_sqrt_csv):
        try:
            dasatom_sqrt_df = pd.read_csv(dasatom_sqrt_csv)
            out["DasAtom (sqrt N)"] = dasatom_sqrt_df
            print(f"Loaded DasAtom (sqrt N) data from: {dasatom_sqrt_csv}")
        except Exception as e:
            print(f"Warning: Failed to load DasAtom (sqrt N) CSV {dasatom_sqrt_csv}: {e}")
    
    # Try to load Enola data
    enola_csv = os.path.join(csv_dir, f"enola_{dataset}_results.csv")
    if os.path.exists(enola_csv):
        try:
            enola_df = pd.read_csv(enola_csv)
            out["Enola"] = enola_df
            print(f"Loaded Enola data from: {enola_csv}")
        except Exception as e:
            print(f"Warning: Failed to load Enola CSV {enola_csv}: {e}")
    
    return out


def ensure_ladder_order(data: Dict[str, pd.DataFrame]) -> List[Tuple[str, pd.DataFrame]]:
    present = set(data.keys())
    
    # DasAtom and Enola go first if present
    ordered = []
    if "DasAtom (sqrt N)" in present:
        ordered.append(("DasAtom (sqrt N)", data["DasAtom (sqrt N)"]))
    if "DasAtom (1.2x)" in present:
        ordered.append(("DasAtom (1.2x)", data["DasAtom (1.2x)"]))
    if "Enola" in present:
        ordered.append(("Enola", data["Enola"]))

    # Then add variants in ladder order
    ordered.extend([(v, data[v]) for v in LADDER_ORDER if v in present])
    
    special_variants = {"DasAtom (sqrt N)", "DasAtom (1.2x)", "Enola"}
    missing = [v for v in LADDER_ORDER if v not in present and v not in special_variants]
    extras = [v for v in data.keys() if v not in set(LADDER_ORDER) and v not in special_variants]
    if missing and len(data) > 1:  # Only warn if we're expecting multiple variants
        print("Info: variants not present:", ", ".join(missing))
    if extras:
        print("Info: extra variants (will be appended):", ", ".join(extras))
        ordered.extend([(v, data[v]) for v in sorted(extras)])
    return ordered


def coerce_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")

def plot_boxplots_by_variant(
    ordered: List[Tuple[str, pd.DataFrame]],
    feature: str,
    dataset: str,
    out_dir: str,
):
    labels = []
    values = []

    for variant, df in ordered:
        if feature not in df.columns:
            continue
        y = coerce_numeric(df, feature).dropna().to_numpy()
        if y.size == 0:
            continue
        labels.append(pretty_name(variant))
        values.append(y)

    # If it's a Fidelity feature, let's also compute and plot the Max Fidelity distribution as an extra column
    if 'Fidelity' in feature:
        # Check if we can compute max fidelity using "Num CZ Gates" (0.995^N)
        for variant, df in ordered:
            if 'Num CZ Gates' in df.columns:
                max_fidelity = 0.995 ** df['Num CZ Gates']
                valid_y = pd.to_numeric(max_fidelity, errors="coerce").dropna().to_numpy()
                if valid_y.size > 0:
                    labels.append('Max (Gate Loss Only)')
                    values.append(valid_y)
                    break

    if not values:
        return

    plt.figure(figsize=(max(10, len(labels) * 1.5), 6))
    plt.boxplot(values, tick_labels=labels, showmeans=True)
    plt.xticks(rotation=30, ha="right")
    plt.title(f"{dataset}: {feature} (by ladder variant)")
    plt.ylabel(feature)
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()

    safe = feature.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
    out_path = os.path.join(out_dir, f"{dataset}_ladder_box_{safe}.pdf")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_mean_line_by_variant(
    ordered: List[Tuple[str, pd.DataFrame]],
    feature: str,
    dataset: str,
    out_dir: str,
):
    labels = []
    means = []

    for variant, df in ordered:
        if feature not in df.columns:
            print(f"  DEBUG: {variant} missing column '{feature}'")
            continue
        y = coerce_numeric(df, feature)
        y = y.dropna()
        if y.empty:
            print(f"  DEBUG: {variant} has empty data for '{feature}'")
            continue
        labels.append(pretty_name(variant))
        means.append(float(y.mean()))
        print(f"Mean {feature} for {pretty_name(variant)}: {means[-1]:.4f}")

    if 'Fidelity' in feature:
        for variant, df in ordered:
            if 'Num CZ Gates' in df.columns:
                max_fidelity = 0.995 ** df['Num CZ Gates']
                valid_y = pd.to_numeric(max_fidelity, errors="coerce").dropna()
                if not valid_y.empty:
                    labels.append('Max (Gate Loss Only)')
                    means.append(float(valid_y.mean()))
                    print(f"Mean Max (Gate Loss Only) computed: {means[-1]:.4f}")
                    break

    if not means:
        return

    plt.figure(figsize=(max(10, len(labels) * 1.5), 4))
    x = np.arange(len(labels))
    plt.plot(x, means, marker="o", linewidth=2)
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.title(f"{dataset}: mean {feature} (ladder)")
    plt.ylabel(f"Mean {feature}")
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()

    safe = feature.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
    out_path = os.path.join(out_dir, f"{dataset}_ladder_mean_{safe}.pdf")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True, help="e.g. qft or tetris")
    parser.add_argument("--csv-dir", type=str, default="results/qft_ladder_rint2")
    parser.add_argument("--out-dir", type=str, default=None)
    parser.add_argument("--variants", type=str, default=None, help="Comma-separated list of variants to include (e.g., 'DasAtom,4_CoM_subset,8_optimized_eviction')")
    parser.add_argument("--qft-step", type=int, default=None, help="If set, only include qft_N where N is multiple of this step (e.g. 5 for qft_5,10,...). Max supported up to 60.")
    args = parser.parse_args()

    out_dir = args.out_dir or os.path.join("plots", f"{args.dataset}_ladder")
    os.makedirs(out_dir, exist_ok=True)

    data = load_ladder_csvs(args.dataset, args.csv_dir)
    # Optional filter to only include qft circuits at a given step (e.g., 5)
    if args.qft_step and args.dataset.lower() == "qft":
        step = int(args.qft_step)
        for k, df in list(data.items()):
            if "QASM File" in df.columns:
                nums = df["QASM File"].astype(str).str.extract(r"qft_(\d+)", expand=False)
                nums = pd.to_numeric(nums, errors='coerce')
                keep = (nums.notna()) & (nums % step == 0) & (nums >= step) & (nums <= 60)
                data[k] = df[keep.fillna(False)].copy()
            else:
                data[k] = df
    
    # Filter variants if specified
    if args.variants:
        selected = [v.strip() for v in args.variants.split(',')]
        data = {k: v for k, v in data.items() if k in selected}
        print(f"Filtered to variants: {list(data.keys())}")
    
    ordered = ensure_ladder_order(data)

    # Consistent ordering of circuits inside each CSV (not required for box/mean plots, but keeps sanity)
    for _, df in ordered:
        if "QASM File" in df.columns:
            df.sort_values("QASM File", key=naturalize_series, inplace=True)

    for feature in FEATURES_TO_PLOT:
        plot_boxplots_by_variant(ordered, feature, args.dataset, out_dir)
        plot_mean_line_by_variant(ordered, feature, args.dataset, out_dir)

    print(f"Saved ladder plots to: {out_dir}")


if __name__ == "__main__":
    main()
