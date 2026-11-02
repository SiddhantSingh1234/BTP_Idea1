import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import re
import argparse
import glob
from typing import Optional

# Try optional Plotly import for interactive plots
try:
    import plotly.graph_objects as go
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False

# Define the CSV files for each category
qft_files = {
    'Final': 'results/qft_ladder/qft_compiler_results_final2.csv',
    'Final_newparam_anticrowd': 'results/qft_ladder/qft_compiler_results_final_newparam_anticrowd.csv',
    'newparam_right_filled_dynamic_layout': 'results/qft_ladder/qft_compiler_results_newparam_right_filled_dynamic_layout.csv',
    'newparam_right_filled_dynamic_layout2': 'results/qft_ladder/qft_compiler_results_newparam_right_filled_dynamic_layout2.csv',
}

tetris_files = {
    'Final': 'results/tetris_ladder/tetris_compiler_results_final2.csv',
    'Final_newparam_anticrowd': 'results/tetris_ladder/tetris_compiler_results_final_newparam_anticrowd.csv',
    'newparam_right_filled_dynamic_layout': 'results/tetris_ladder/tetris_compiler_results_newparam_right_filled_dynamic_layout.csv',
    'newparam_right_filled_dynamic_layout2': 'results/tetris_ladder/tetris_compiler_results_newparam_right_filled_dynamic_layout2.csv',
}

# Ladder ordering (variant names produced by benchmark_runner.py)
LADDER_ORDER = [
    "1_all_random",
    "2_greedy_nearest_idle_parking",
    "3_hungarian",
    "4_CoM_subset",
    "5_rft_idle_parking",
    "6_dynamic_slot_0q_move",
    "7_dynamic_slot_01q_move",
    "8_optimized_eviction",
    "9_perimeter_staging",
    "10_asap_packager",
    "11_auto_tuning",
]

def pretty_ladder_label(variant: str) -> str:
    # Map specific variants to display names
    name_mapping = {
        "4_CoM_subset": "Method A",
        "8_optimized_eviction": "Method B",
    }
    return name_mapping.get(variant, variant)


# Optional global filter for QFT step (e.g., 5 to plot qft_5, qft_10, ...)
QFT_FILTER_STEP: Optional[int] = None

# Optional Excel summary files
qft_summary_excel = 'qft_summary.xlsx'
tetris_summary_excel = 'tetris_summary.xlsx'

# Features to plot (excluding QASM File and Num Qubit)
features_to_plot = [
    "Num CZ Gates", "Circuit Depth", "Fidelity (DasAtom Model)", 
    "Fidelity (Realistic)", "Movement Fidelity", "Num Movement Ops", 
    "Num Transferred Qubits", "Num Moves", "Total Move Distance", 
    "Num Partitions", "Num Gate Cycles", "Elapsed Time (s)", 
    "Total_T (us)", "Idle Time (us)"
]

def load_data(files_dict, csv_dir):
    """Load all CSV files for a category"""
    data_dict = {}
    for name, file in files_dict.items():
        filepath = os.path.join(csv_dir, file)
        if not os.path.exists(filepath):
            print(f"Warning: missing CSV: {filepath}")
            continue
        df = pd.read_csv(filepath)
        # Ensure fidelity columns exist
        df = ensure_fidelity_columns(df)
        data_dict[name] = df
    return data_dict

def load_ladder_files(dataset: str, csv_dir: str) -> dict:
    """Return a {variant: filename} dict for ladder CSV outputs."""
    pattern = os.path.join(csv_dir, f"{dataset}_ladder_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"Warning: no ladder CSVs found for '{dataset}' (pattern: {pattern})")
        return {}

    variant_to_file = {}
    for fp in files:
        base = os.path.basename(fp)
        if not base.startswith(f"{dataset}_ladder_") or not base.endswith(".csv"):
            continue
        variant = base[len(f"{dataset}_ladder_") : -len(".csv")]
        variant_to_file[variant] = base

    out = {}
    for v in LADDER_ORDER:
        if v in variant_to_file:
            out[v] = variant_to_file[v]
    for v in sorted(set(variant_to_file.keys()) - set(LADDER_ORDER)):
        out[v] = variant_to_file[v]
    return out

def naturalize_series(s: pd.Series) -> pd.Series:
    """Return a series transformed for natural sorting (qft1, qft2, qft10)."""
    return s.astype(str).str.lower().str.replace(
        r'\d+', lambda m: f"{int(m.group()):08d}", regex=True
    )

def ensure_fidelity_columns(df: pd.DataFrame) -> pd.DataFrame:
    if 'Fidelity' in df.columns:
        if 'Fidelity (DasAtom Model)' not in df.columns:
            df['Fidelity (DasAtom Model)'] = df['Fidelity']
    if 'Num CZ Gates' in df.columns:
        df['Max Fidelity'] = 0.995 ** df['Num CZ Gates']
    return df

def plot_feature(data_dict, feature, category_name, output_dir):
    """Create a plot for a specific feature across all optimization levels, aligned by QASM File"""
    plt.figure(figsize=(14, 6))
    colors = list(plt.cm.tab10.colors) + list(plt.cm.Set3.colors)
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'P', 'X', '*', 'h', 'H']
    
    # 1. Collect all unique QASM Files and filter according to QFT step
    all_qasm_files = set()
    for df in data_dict.values():
        if 'QASM File' in df.columns:
            all_qasm_files.update(df['QASM File'].astype(str).tolist())
    
    filtered_files = []
    for f in all_qasm_files:
        if 'qft_' in f:
            match = re.search(r'qft_(\d+)', f)
            if match:
                num = int(match.group(1))
                if QFT_FILTER_STEP:
                    if num % QFT_FILTER_STEP == 0 and QFT_FILTER_STEP <= num <= 60:
                        filtered_files.append(f)
                else:
                    if num % 10 == 0 and 10 <= num <= 100:
                        filtered_files.append(f)
        else:
            filtered_files.append(f)
    
    if not filtered_files:
        plt.close()
        return

    if 'TETRIS' in category_name.upper():
        sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r'_(\d+)', x).group(1)) if re.search(r'_(\d+)', x) else 0)
    else:
        sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r'qft_(\d+)', x).group(1)) if re.search(r'qft_(\d+)', x) else 0)
    file_to_idx = {f: i for i, f in enumerate(sorted_files)}
    x_indices = np.arange(len(sorted_files))
    
    valid_series_count = 0
    max_fidelity_plotted = False
    
    for idx, (name, df) in enumerate(data_dict.items()):
        if feature in df.columns:
            y_values = [np.nan] * len(sorted_files)
            found_data = False
            for _, row in df.iterrows():
                fname = str(row['QASM File'])
                if fname in file_to_idx:
                    val = pd.to_numeric(row[feature], errors='coerce')
                    if not pd.isna(val):
                        y_values[file_to_idx[fname]] = val
                        found_data = True
            
            if not found_data: continue
            y = np.array(y_values)
            display_name = pretty_ladder_label(name)
            mask = ~np.isnan(y)
            if any(mask):
                valid_series_count += 1
                plt.plot(x_indices[mask], y[mask], marker=markers[idx % len(markers)],
                         label=display_name, color=colors[idx % len(colors)],
                         linewidth=1.5, markersize=6, alpha=0.8)
                         
            # Try to plot Max Fidelity as a dotted line if this is a Fidelity plot
            if 'Fidelity' in feature and 'Max Fidelity' in df.columns and not max_fidelity_plotted:
                mf_y_values = [np.nan] * len(sorted_files)
                for _, row in df.iterrows():
                    fname = str(row['QASM File'])
                    if fname in file_to_idx:
                        val = pd.to_numeric(row['Max Fidelity'], errors='coerce')
                        if not pd.isna(val):
                            mf_y_values[file_to_idx[fname]] = val
                mf_y = np.array(mf_y_values)
                mf_mask = ~np.isnan(mf_y)
                if any(mf_mask):
                    plt.plot(x_indices[mf_mask], mf_y[mf_mask], linestyle='--', 
                             label='Max Fidelity (Gate Loss Only)', color='black',
                             linewidth=2.0, alpha=0.8)
                    max_fidelity_plotted = True
    
    if valid_series_count == 0:
        plt.close()
        return

    plt.xticks(x_indices, sorted_files, rotation=45, ha='right', fontsize=9)
    plt.xlabel('Circuit', fontsize=11)
    plt.ylabel(feature, fontsize=11)
    plt.title(f'{category_name}: {feature}', fontsize=13, fontweight='bold')
    plt.legend(loc='best', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    safe_filename = feature.replace(' ', '_').replace('(', '').replace(')', '')
    output_path = os.path.join(output_dir, f'{category_name.lower()}_{safe_filename}.pdf')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved: {output_path}')

def plot_feature_interactive(data_dict, feature, category_name, output_dir_html):
    if not PLOTLY_AVAILABLE: return

    all_qasm_files = set()
    for df in data_dict.values():
        if 'QASM File' in df.columns:
            all_qasm_files.update(df['QASM File'].astype(str).tolist())
    
    filtered_files = []
    for f in all_qasm_files:
        if 'qft_' in f:
            match = re.search(r'qft_(\d+)', f)
            if match:
                num = int(match.group(1))
                if QFT_FILTER_STEP:
                    if num % QFT_FILTER_STEP == 0 and QFT_FILTER_STEP <= num <= 60:
                        filtered_files.append(f)
                else:
                    if num % 10 == 0 and 10 <= num <= 100:
                        filtered_files.append(f)
        else:
            filtered_files.append(f)
    
    if not filtered_files: return

    if 'TETRIS' in category_name.upper():
        sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r'_(\d+)', x).group(1)) if re.search(r'_(\d+)', x) else 0)
    else:
        sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r'qft_(\d+)', x).group(1)) if re.search(r'qft_(\d+)', x) else 0)
    file_to_idx = {f: i for i, f in enumerate(sorted_files)}
    x_indices = np.arange(len(sorted_files))

    fig = go.Figure()

    for idx, (name, df) in enumerate(data_dict.items()):
        if feature not in df.columns: continue
        y_values = [None] * len(sorted_files)
        found_data = False
        for _, row in df.iterrows():
            fname = str(row['QASM File'])
            if fname in file_to_idx:
                val = pd.to_numeric(row[feature], errors='coerce')
                if not pd.isna(val) :
                    y_values[file_to_idx[fname]] = val
                    found_data = True
        if not found_data: continue
        display_name = pretty_ladder_label(name)
        fig.add_trace(go.Scatter(x=x_indices, y=y_values, mode='lines+markers',
                                name=display_name, hovertemplate='Circuit: %{customdata}<br>' + feature + ': %{y}<extra></extra>',
                                customdata=np.array(sorted_files), connectgaps=True))

    fig.update_layout(title=f"{category_name}: {feature}",
                      xaxis=dict(tickmode='array', tickvals=x_indices, ticktext=sorted_files),
                      xaxis_title='Circuit', yaxis_title=feature, template='plotly_white')

    safe_filename = feature.replace(' ', '_').replace('(', '').replace(')', '')
    output_path = os.path.join(output_dir_html, f'{category_name.lower()}_{safe_filename}.html')
    try:
        pio.write_html(fig, file=output_path, include_plotlyjs='cdn', auto_open=False)
    except Exception: pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", type=str, default="results/qft_ladder_rint2")
    parser.add_argument("--mode", type=str, choices=["legacy", "ladder", "both"], default="both")
    parser.add_argument("--datasets", type=str, default="both", help="Which datasets to plot")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--variants", type=str, default=None)
    parser.add_argument("--qft-step", type=int, default=None, help="If set, only include qft_N where N is multiple of this step (e.g. 5 for qft_5,10,...). Max supported up to 60.")
    args = parser.parse_args()

    csv_dir = args.csv_dir
    out_dir = args.output_dir or "plots/qft_total_comparison"
    os.makedirs(out_dir, exist_ok=True)
    interactive_output_dir = os.path.join(out_dir, "interactive")
    os.makedirs(interactive_output_dir, exist_ok=True)

    def build_files(dataset: str) -> dict:
        files = {}
        if args.mode in ("legacy", "both"):
            if dataset == "qft": files.update(qft_files)
            elif dataset == "tetris": files.update(tetris_files)
        if args.mode in ("ladder", "both"):
            ladder_files = load_ladder_files(dataset, csv_dir)
            if args.variants:
                selected_variants = [v.strip() for v in args.variants.split(',')]
                ladder_files = {k: v for k, v in ladder_files.items() if k in selected_variants}
            files.update(ladder_files)
        return files

    dataset_list = ["qft_total"] if args.datasets == "qft_total" else (["qft", "tetris"] if args.datasets == "both" else [args.datasets])

    for ds in dataset_list:
        print(f"Loading {ds} data...")
        # Apply optional QFT step filter
        global QFT_FILTER_STEP
        QFT_FILTER_STEP = args.qft_step

        ds_data = load_data(build_files(ds), csv_dir)
        # Try to load DasAtom data
        if ds == 'tetris':
            ds_csv_path = os.path.join('results/qtetris_compiled_csv', f"qtetris_dasatom_1.2x.csv")
            ds_sqrt_path = os.path.join('results/qtetris_compiled_csv', f"qtetris_dasatom.csv")
        else:
            ds_csv_path = os.path.join('results/qft_step5_ladder_rint2', f"dasatom_qft_step5_1.2x_results.csv")
            ds_sqrt_path = os.path.join('results/qft_step5_ladder_rint2', f"dasatom_qft_step5_results.csv")
        
        if os.path.exists(ds_csv_path):
            try:
                ds_summary_df = pd.read_csv(ds_csv_path)
                if len(ds_summary_df.columns) == 1: ds_summary_df = pd.read_csv(ds_csv_path, sep='\t')
                ds_data["DasAtom (1.2x)"] = ensure_fidelity_columns(ds_summary_df)
                print(f"Loaded DasAtom (1.2x) data from CSV: {ds_csv_path}")
            except Exception: pass

        if os.path.exists(ds_sqrt_path):
            try:
                ds_sqrt_df = pd.read_csv(ds_sqrt_path)
                if len(ds_sqrt_df.columns) == 1: ds_sqrt_df = pd.read_csv(ds_sqrt_path, sep='\t')
                ds_data["DasAtom (sqrt N)"] = ensure_fidelity_columns(ds_sqrt_df)
                print(f"Loaded DasAtom (sqrt N) data from CSV: {ds_sqrt_path}")
            except Exception: pass
        
        # Try to load Enola data
        enola_csv_path = os.path.join(csv_dir, f"enola_{ds}_results.csv")
        if ds == "qft_total" and not os.path.exists(enola_csv_path):
            enola_csv_path = os.path.join(csv_dir, "enola_qft_results.csv")
        if os.path.exists(enola_csv_path):
            try:
                enola_df = pd.read_csv(enola_csv_path)
                if len(enola_df.columns) == 1: enola_df = pd.read_csv(enola_csv_path, sep='\t')
                ds_data["Enola"] = ensure_fidelity_columns(enola_df)
                print(f"Loaded Enola data from CSV: {enola_csv_path}")
            except Exception: pass

        print(f"Generating {ds} plots...")
        for feature in features_to_plot:
            plot_feature(ds_data, feature, ds.upper(), out_dir)
            plot_feature_interactive(ds_data, feature, ds.upper(), interactive_output_dir)

    print(f"\nAll plots saved to '{out_dir}' directory!")

if __name__ == '__main__':
    main()