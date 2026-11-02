#!/usr/bin/env python3
"""
Generate comparison plots for QFT step5 circuits in final_plot.py style.
Plots Our Approach and DasAtom for 11x11 and 35x35 grids.
"""

import argparse
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Features to plot
features_to_plot = [
    'Num CZ Gates', 'Circuit Depth', 'Fidelity (DasAtom Model)', 
    'Movement Fidelity', 'Num Movement Ops',
    'Num Transferred Qubits', 'Num Moves', 'Total Move Distance',
    'Num Gate Cycles', 'Elapsed Time (s)',
    'Total_T (us)', 'Idle Time (us)'
]

# Display names for features (maps CSV column name to display label)
display_names = {
    'Elapsed Time (s)': 'Compilation Time (s)',
    'Total_T (us)': 'Circuit Runtime (us)',
}

def load_data(variant_name, base_path):
    """Load all QFT data from different grid configurations."""
    data = {}

    # DasAtom 11x11
    dasatom_11_path = os.path.join(base_path, "qft_step5_ladder_rint2", "dasatom_qft_step5_results.csv")
    if os.path.exists(dasatom_11_path):
        data['DasAtom 11x11'] = pd.read_csv(dasatom_11_path)

    # DasAtom 20x20
    dasatom_20_path = os.path.join(base_path, "qft_step5_20x20_ladder_rint2", "dasatom_qft_step5_20x20_results.csv")
    if os.path.exists(dasatom_20_path):
        data['DasAtom 20x20'] = pd.read_csv(dasatom_20_path)

    # DasAtom 35x35
    dasatom_35_path = os.path.join(base_path, "qft_step5_35x35_ladder_rint2", "dasatom_qft_step5_35x35_results.csv")
    if os.path.exists(dasatom_35_path):
        data['DasAtom 35x35'] = pd.read_csv(dasatom_35_path)

# Our Approach 11x11
    method_b_11_path = os.path.join(base_path, variant_name, "qft_step5_11x11_final_ladder_rint2", f"qft_step5_11x11_final_ladder_{variant_name}.csv")
    if os.path.exists(method_b_11_path):
        data['Our Approach 11x11'] = pd.read_csv(method_b_11_path)

    # Our Approach 20x20
    method_b_20_path = os.path.join(base_path, variant_name, "qft_step5_20x20_final_ladder_rint2", f"qft_step5_20x20_final_ladder_{variant_name}.csv")
    if os.path.exists(method_b_20_path):
        data['Our Approach 20x20'] = pd.read_csv(method_b_20_path)

    # Our Approach 35x35
    method_b_35_path = os.path.join(base_path, variant_name, "qft_step5_final_ladder_rint2", f"qft_step5_final_ladder_{variant_name}.csv")
    if os.path.exists(method_b_35_path):
        data['Our Approach 35x35'] = pd.read_csv(method_b_35_path)

    return data

def normalize_circuit_name(name):
    """Extract circuit name from QASM filename."""
    return name.replace('.qasm', '').strip()

def plot_feature(data_dict, feature, output_dir):
    """Create a plot for a specific feature across all configurations, aligned by QASM File"""
    plt.figure(figsize=(14, 6))
    
    # Define colors and markers for each configuration
    styles = {
        'DasAtom 11x11': {'color': '#1f77b4', 'marker': 'o', 'linestyle': '-'},
        'DasAtom 20x20': {'color': '#ff7f0e', 'marker': 's', 'linestyle': '-'},
        'DasAtom 35x35': {'color': '#2ca02c', 'marker': '^', 'linestyle': '-'},
        'Our Approach 11x11': {'color': '#d62728', 'marker': 'D', 'linestyle': '--'},
        'Our Approach 20x20': {'color': '#9467bd', 'marker': 'v', 'linestyle': '--'},
        'Our Approach 35x35': {'color': '#8c564b', 'marker': '<', 'linestyle': '--'},
    }
    
    # 1. Collect all unique QASM Files
    all_qasm_files = set()
    for df in data_dict.values():
        if 'QASM File' in df.columns:
            all_qasm_files.update(df['QASM File'].astype(str).tolist())
    
    # Filter for QFT step5 circuits (qft_5, qft_10, qft_15, ...)
    filtered_files = []
    for f in all_qasm_files:
        match = re.search(r'qft_(\d+)', f)
        if match:
            num = int(match.group(1))
            # Include step-5 circuits from 5 to 60
            if num % 5 == 0 and 5 <= num <= 60:
                filtered_files.append(f)
    
    if not filtered_files:
        plt.close()
        return

    # Sort by numeric value
    sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r'qft_(\d+)', x).group(1)))
    file_to_idx = {f: i for i, f in enumerate(sorted_files)}
    x_indices = np.arange(len(sorted_files))
    
    # Extract just the number for x-axis labels
    x_labels = [re.search(r'qft_(\d+)', f).group(1) for f in sorted_files]
    
    valid_series_count = 0
    for name, df in data_dict.items():
        if feature not in df.columns:
            continue
            
        y_values = [np.nan] * len(sorted_files)
        found_data = False
        
        for _, row in df.iterrows():
            fname = str(row['QASM File'])
            if fname in file_to_idx:
                val = pd.to_numeric(row[feature], errors='coerce')
                if not pd.isna(val):
                    y_values[file_to_idx[fname]] = val
                    found_data = True
        
        if not found_data:
            continue
            
        y = np.array(y_values)
        mask = ~np.isnan(y)
        
        if any(mask):
            valid_series_count += 1
            style = styles.get(name, {'color': 'gray', 'marker': 'o', 'linestyle': '-'})
            plt.plot(x_indices[mask], y[mask], 
                    marker=style['marker'],
                    label=name, 
                    color=style['color'],
                    linestyle=style['linestyle'],
                    linewidth=3, 
                    markersize=12, 
                    alpha=0.85)
    
    if valid_series_count == 0:
        plt.close()
        return

    # Get display name for the feature
    display_name = display_names.get(feature, feature)
    
    plt.xticks(x_indices, x_labels, fontsize=20)
    plt.yticks(fontsize=20)
    plt.xlabel('QFT Circuit Size (number of qubits)', fontsize=20, fontweight='bold')
    plt.ylabel(display_name, fontsize=20, fontweight='bold')
    plt.title(f'QFT: {display_name}', fontsize=20, fontweight='bold')
    plt.legend(loc='best', fontsize=22, framealpha=0.9)
    plt.grid(True, linestyle='--', alpha=0.4)
    
    # Use log scale for fidelity
    if 'Fidelity' in feature:
        plt.yscale('log')
    
    plt.tight_layout()
    
    safe_filename = feature.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
    output_path = os.path.join(output_dir, f'qft_{safe_filename}.pdf')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved: {output_path}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="results",
                        help="Directory containing benchmark result CSVs (default: results)")
    parser.add_argument("--plots-dir", default="plots",
                        help="Directory to write generated PDF plots (default: plots)")
    parser.add_argument("--variants", nargs="+",
                        default=["9_perimeter_staging", "10_asap_packager", "11_auto_tuning"],
                        help="Variant subdirectory names to process")
    args = parser.parse_args()

    for variant in args.variants:
        print(f"\n--- Loading QFT step5 data for variant: {variant} ---")
        data = load_data(variant, args.results_dir)

        print(f"Loaded {len(data)} configurations:")
        for config_name, df in data.items():
            print(f"  {config_name}: {len(df)} circuits")

        output_dir = os.path.join(args.plots_dir, variant, "qft_grid_comparison_OPTIMIZED")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\nGenerating comparison plots for {variant}...")
        for feature in features_to_plot:
            plot_feature(data, feature, output_dir)

        print(f"\nplots saved to: {output_dir}")


if __name__ == "__main__":
    main()
