#!/usr/bin/env python3
"""
Create comprehensive comparison table for Q_Tetris benchmark circuits.
Compares DasAtom, Method B, and Enola across different grid sizes.
"""

import argparse
import os
import re

import pandas as pd


def normalize_circuit_name(name):
    """Normalize circuit names to match across different datasets.
    
    Only removes .qasm extension. Circuit names like 4gt13_92, hwb5_53, 
    ising_model_10 etc. are complete names - don't remove any numeric suffixes.
    """
    # Remove .qasm extension only
    name = name.replace('.qasm', '')
    
    # Just strip whitespace, preserve case
    name = name.strip()
    
    return name


def load_enola_data(csv_path):
    """Load Enola results."""
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    df['Circuit_Normalized'] = df['Circuit'].apply(normalize_circuit_name)
    return df


def load_dasatom_data(csv_path, grid_label):
    """Load DasAtom results."""
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    df['Circuit_Normalized'] = df['QASM File'].apply(normalize_circuit_name)
    df['Grid'] = grid_label
    return df


def load_method_b_data(csv_path, grid_label):
    """Load Method B results."""
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    df['Circuit_Normalized'] = df['QASM File'].apply(normalize_circuit_name)
    df['Grid'] = grid_label
    return df


def create_comparison_table(variant_name, base_dir):
    """Create comprehensive comparison table."""
    # Load all datasets
    enola_df = load_enola_data(os.path.join(base_dir, "qtetris_enola_results.csv"))

    # DasAtom data
    dasatom_11 = load_dasatom_data(os.path.join(base_dir, "qtetris_ladder_rint2", "dasatom_qtetris_results.csv"), "11x11")
    dasatom_35 = load_dasatom_data(os.path.join(base_dir, "qtetris_35x35_ladder_rint2", "dasatom_qtetris_35x35_results.csv"), "35x35")
    dasatom_12x = load_dasatom_data(os.path.join(base_dir, "qtetris_ladder_rint2", "dasatom_qtetris_1.2x_results.csv"), "1.2xsqrtN")

    # Method B data
    method_b_11 = load_method_b_data(os.path.join(base_dir, variant_name, "qtetris_ladder_rint2", f"qtetris_ladder_{variant_name}.csv"), "11x11")
    method_b_35 = load_method_b_data(os.path.join(base_dir, variant_name, "qtetris_35x35_ladder_rint2", f"qtetris_35x35_ladder_{variant_name}.csv"), "35x35")

    # Get all unique circuits from Enola (master list); fall back to other sources if Enola data is missing
    if enola_df is not None:
        circuits = enola_df['Circuit_Normalized'].unique()
    else:
        all_circuits = set()
        for df in [dasatom_11, dasatom_35, dasatom_12x, method_b_11, method_b_35]:
            if df is not None:
                all_circuits.update(df['Circuit_Normalized'].unique())
        if not all_circuits:
            print(f"[{variant_name}] No input data found under {base_dir}. Skipping.")
            return None
        circuits = sorted(all_circuits)
    
    # Initialize result table
    results = []
    
    for circuit in sorted(circuits):
        row = {'Circuit': circuit}
        
        # Enola data
        if enola_df is not None:
            enola_row = enola_df[enola_df['Circuit_Normalized'] == circuit]
        else:
            enola_row = None
        if enola_row is not None and not enola_row.empty:
            row['Enola_Compile_Time'] = enola_row['Elapsed Time (s)'].values[0]
            row['Enola_Fidelity'] = enola_row['Fidelity (DasAtom Model)'].values[0]
            row['Enola_Move_Ops'] = enola_row['Num Movement Ops'].values[0]
        else:
            row['Enola_Compile_Time'] = None
            row['Enola_Fidelity'] = None
            row['Enola_Move_Ops'] = None
        
        # 11x11 grid data
        if dasatom_11 is not None:
            d11 = dasatom_11[dasatom_11['Circuit_Normalized'] == circuit]
            if not d11.empty:
                row['DasAtom_11x11_Compile_Time'] = d11['Elapsed Time (s)'].values[0]
                row['DasAtom_11x11_Fidelity'] = d11['Fidelity (DasAtom Model)'].values[0]
                row['DasAtom_11x11_Move_Ops'] = d11['Num Movement Ops'].values[0]
            else:
                row['DasAtom_11x11_Compile_Time'] = None
                row['DasAtom_11x11_Fidelity'] = None
                row['DasAtom_11x11_Move_Ops'] = None
        else:
            row['DasAtom_11x11_Compile_Time'] = None
            row['DasAtom_11x11_Fidelity'] = None
            row['DasAtom_11x11_Move_Ops'] = None
        
        if method_b_11 is not None:
            m11 = method_b_11[method_b_11['Circuit_Normalized'] == circuit]
            if not m11.empty:
                row['MethodB_11x11_Compile_Time'] = m11['Elapsed Time (s)'].values[0]
                row['MethodB_11x11_Fidelity'] = m11['Fidelity (DasAtom Model)'].values[0]
                row['MethodB_11x11_Move_Ops'] = m11['Num Movement Ops'].values[0]
            else:
                row['MethodB_11x11_Compile_Time'] = None
                row['MethodB_11x11_Fidelity'] = None
                row['MethodB_11x11_Move_Ops'] = None
        else:
            row['MethodB_11x11_Compile_Time'] = None
            row['MethodB_11x11_Fidelity'] = None
            row['MethodB_11x11_Move_Ops'] = None
        
        # 35x35 grid data
        if dasatom_35 is not None:
            d35 = dasatom_35[dasatom_35['Circuit_Normalized'] == circuit]
            if not d35.empty:
                row['DasAtom_35x35_Compile_Time'] = d35['Elapsed Time (s)'].values[0]
                row['DasAtom_35x35_Fidelity'] = d35['Fidelity (DasAtom Model)'].values[0]
                row['DasAtom_35x35_Move_Ops'] = d35['Num Movement Ops'].values[0]
            else:
                row['DasAtom_35x35_Compile_Time'] = None
                row['DasAtom_35x35_Fidelity'] = None
                row['DasAtom_35x35_Move_Ops'] = None
        else:
            row['DasAtom_35x35_Compile_Time'] = None
            row['DasAtom_35x35_Fidelity'] = None
            row['DasAtom_35x35_Move_Ops'] = None
        
        if method_b_35 is not None:
            m35 = method_b_35[method_b_35['Circuit_Normalized'] == circuit]
            if not m35.empty:
                row['MethodB_35x35_Compile_Time'] = m35['Elapsed Time (s)'].values[0]
                row['MethodB_35x35_Fidelity'] = m35['Fidelity (DasAtom Model)'].values[0]
                row['MethodB_35x35_Move_Ops'] = m35['Num Movement Ops'].values[0]
            else:
                row['MethodB_35x35_Compile_Time'] = None
                row['MethodB_35x35_Fidelity'] = None
                row['MethodB_35x35_Move_Ops'] = None
        else:
            row['MethodB_35x35_Compile_Time'] = None
            row['MethodB_35x35_Fidelity'] = None
            row['MethodB_35x35_Move_Ops'] = None
        
        # 1.2xsqrtN grid data (DasAtom only)
        if dasatom_12x is not None:
            d12x = dasatom_12x[dasatom_12x['Circuit_Normalized'] == circuit]
            if not d12x.empty:
                row['DasAtom_1.2xSqrtN_Compile_Time'] = d12x['Elapsed Time (s)'].values[0]
                row['DasAtom_1.2xSqrtN_Fidelity'] = d12x['Fidelity (DasAtom Model)'].values[0]
                row['DasAtom_1.2xSqrtN_Move_Ops'] = d12x['Num Movement Ops'].values[0]
            else:
                row['DasAtom_1.2xSqrtN_Compile_Time'] = None
                row['DasAtom_1.2xSqrtN_Fidelity'] = None
                row['DasAtom_1.2xSqrtN_Move_Ops'] = None
        else:
            row['DasAtom_1.2xSqrtN_Compile_Time'] = None
            row['DasAtom_1.2xSqrtN_Fidelity'] = None
            row['DasAtom_1.2xSqrtN_Move_Ops'] = None
        
        results.append(row)
    
    # Create DataFrame
    df_result = pd.DataFrame(results)
    
    # Reorder columns for better readability
    column_order = [
        'Circuit',
        # 11x11 grid
        'DasAtom_11x11_Compile_Time', 'DasAtom_11x11_Fidelity', 'DasAtom_11x11_Move_Ops',
        'MethodB_11x11_Compile_Time', 'MethodB_11x11_Fidelity', 'MethodB_11x11_Move_Ops',
        'Enola_Compile_Time', 'Enola_Fidelity', 'Enola_Move_Ops',
        # 35x35 grid
        'DasAtom_35x35_Compile_Time', 'DasAtom_35x35_Fidelity', 'DasAtom_35x35_Move_Ops',
        'MethodB_35x35_Compile_Time', 'MethodB_35x35_Fidelity', 'MethodB_35x35_Move_Ops',
        # 1.2xsqrtN grid
        'DasAtom_1.2xSqrtN_Compile_Time', 'DasAtom_1.2xSqrtN_Fidelity', 'DasAtom_1.2xSqrtN_Move_Ops',
    ]
    
    if not df_result.empty:
        df_result = df_result.reindex(columns=column_order)

    # Save to CSV
    output_path = os.path.join(base_dir, variant_name, "qtetris_comparison_full.csv")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df_result.to_csv(output_path, index=False)
    print(f"Comprehensive comparison table saved to: {output_path}")
    print(f"\nTable dimensions: {df_result.shape[0]} circuits x {df_result.shape[1]} columns")
    print(f"\nFirst 5 rows:")
    print(df_result.head().to_string())
    
    return df_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="results",
                        help="Directory containing benchmark result CSVs (default: results)")
    parser.add_argument("--variants", nargs="+",
                        default=["9_perimeter_staging", "10_asap_packager", "11_auto_tuning"],
                        help="Variant subdirectory names to process")
    args = parser.parse_args()
    for v in args.variants:
        create_comparison_table(v, args.results_dir)
