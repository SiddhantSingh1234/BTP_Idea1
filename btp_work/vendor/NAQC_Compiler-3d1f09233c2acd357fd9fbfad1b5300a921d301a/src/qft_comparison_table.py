#!/usr/bin/env python3
"""
Create comprehensive comparison table for QFT step5 benchmark circuits.
Compares DasAtom (11x11, 35x35, 1.2xsqrtN), Method B (11x11, 35x35), and Enola.
"""

import argparse
import os

import pandas as pd


def normalize_circuit_name(name):
    """Normalize circuit names to match across different datasets."""
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
    # Filter for QFT circuits only (case-insensitive)
    df = df[df['Circuit'].str.lower().str.startswith('qft_')]
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


def create_comparison_table(base_dir, output_path):
    """Create comprehensive comparison table for QFT circuits."""
    # Load all datasets
    # Enola data
    enola_df = load_enola_data(os.path.join(base_dir, "qtetris_enola_results.csv"))
    
    # DasAtom data
    dasatom_11 = load_dasatom_data(
        os.path.join(base_dir, "qft_step5_ladder_rint2", "dasatom_qft_step5_results.csv"), 
        "11x11"
    )
    dasatom_35 = load_dasatom_data(
        os.path.join(base_dir, "qft_step5_35x35_ladder_rint2", "dasatom_qft_step5_35x35_results.csv"), 
        "35x35"
    )
    dasatom_12x = load_dasatom_data(
        os.path.join(base_dir, "qft_step5_ladder_rint2", "dasatom_qft_step5_1.2x_results.csv"), 
        "1.2xsqrtN"
    )
    
    # Method B data
    method_b_11 = load_method_b_data(
        os.path.join(base_dir, "qft_step5_ladder_rint2", "qft_step5_ladder_8_optimized_eviction.csv"), 
        "11x11"
    )
    method_b_35 = load_method_b_data(
        os.path.join(base_dir, "qft_step5_35x35_ladder_rint2", "qft_step5_35x35_ladder_8_optimized_eviction.csv"), 
        "35x35"
    )
    
    # Get all unique circuits from all datasets
    all_circuits = set()
    for df in [dasatom_11, dasatom_35, dasatom_12x, method_b_11, method_b_35]:
        if df is not None:
            all_circuits.update(df['Circuit_Normalized'].unique())
    if enola_df is not None:
        all_circuits.update(enola_df['Circuit_Normalized'].unique())
    
    circuits = sorted(all_circuits)
    
    # Initialize result table
    results = []
    
    for circuit in circuits:
        row = {'Circuit': circuit}
        
        # Enola data
        if enola_df is not None:
            enola_row = enola_df[enola_df['Circuit_Normalized'] == circuit]
            if not enola_row.empty:
                row['Enola_Compile_Time'] = enola_row['Elapsed Time (s)'].values[0]
                row['Enola_Execution_Time'] = None  # Enola doesn't have this metric
                row['Enola_Fidelity'] = enola_row['Fidelity (DasAtom Model)'].values[0]
                row['Enola_Move_Ops'] = enola_row['Num Movement Ops'].values[0]
            else:
                row['Enola_Compile_Time'] = None
                row['Enola_Execution_Time'] = None
                row['Enola_Fidelity'] = None
                row['Enola_Move_Ops'] = None
        
        # DasAtom 11x11 data
        if dasatom_11 is not None:
            d11 = dasatom_11[dasatom_11['Circuit_Normalized'] == circuit]
            if not d11.empty:
                row['DasAtom_11x11_Compile_Time'] = d11['Elapsed Time (s)'].values[0]
                row['DasAtom_11x11_Execution_Time'] = d11['Total_T (us)'].values[0]
                row['DasAtom_11x11_Fidelity'] = d11['Fidelity (DasAtom Model)'].values[0]
                row['DasAtom_11x11_Move_Ops'] = d11['Num Movement Ops'].values[0]
            else:
                row['DasAtom_11x11_Compile_Time'] = None
                row['DasAtom_11x11_Execution_Time'] = None
                row['DasAtom_11x11_Fidelity'] = None
                row['DasAtom_11x11_Move_Ops'] = None
        
        # DasAtom 35x35 data
        if dasatom_35 is not None:
            d35 = dasatom_35[dasatom_35['Circuit_Normalized'] == circuit]
            if not d35.empty:
                row['DasAtom_35x35_Compile_Time'] = d35['Elapsed Time (s)'].values[0]
                row['DasAtom_35x35_Execution_Time'] = d35['Total_T (us)'].values[0]
                row['DasAtom_35x35_Fidelity'] = d35['Fidelity (DasAtom Model)'].values[0]
                row['DasAtom_35x35_Move_Ops'] = d35['Num Movement Ops'].values[0]
            else:
                row['DasAtom_35x35_Compile_Time'] = None
                row['DasAtom_35x35_Execution_Time'] = None
                row['DasAtom_35x35_Fidelity'] = None
                row['DasAtom_35x35_Move_Ops'] = None
        
        # DasAtom 1.2xsqrtN data
        if dasatom_12x is not None:
            d12x = dasatom_12x[dasatom_12x['Circuit_Normalized'] == circuit]
            if not d12x.empty:
                row['DasAtom_1.2xSqrtN_Compile_Time'] = d12x['Elapsed Time (s)'].values[0]
                row['DasAtom_1.2xSqrtN_Execution_Time'] = d12x['Total_T (us)'].values[0]
                row['DasAtom_1.2xSqrtN_Fidelity'] = d12x['Fidelity (DasAtom Model)'].values[0]
                row['DasAtom_1.2xSqrtN_Move_Ops'] = d12x['Num Movement Ops'].values[0]
            else:
                row['DasAtom_1.2xSqrtN_Compile_Time'] = None
                row['DasAtom_1.2xSqrtN_Execution_Time'] = None
                row['DasAtom_1.2xSqrtN_Fidelity'] = None
                row['DasAtom_1.2xSqrtN_Move_Ops'] = None
        
        # Method B 11x11 data
        if method_b_11 is not None:
            m11 = method_b_11[method_b_11['Circuit_Normalized'] == circuit]
            if not m11.empty:
                row['MethodB_11x11_Compile_Time'] = m11['Elapsed Time (s)'].values[0]
                row['MethodB_11x11_Execution_Time'] = m11['Total_T (us)'].values[0]
                row['MethodB_11x11_Fidelity'] = m11['Fidelity (DasAtom Model)'].values[0]
                row['MethodB_11x11_Move_Ops'] = m11['Num Movement Ops'].values[0]
            else:
                row['MethodB_11x11_Compile_Time'] = None
                row['MethodB_11x11_Execution_Time'] = None
                row['MethodB_11x11_Fidelity'] = None
                row['MethodB_11x11_Move_Ops'] = None
        
        # Method B 35x35 data
        if method_b_35 is not None:
            m35 = method_b_35[method_b_35['Circuit_Normalized'] == circuit]
            if not m35.empty:
                row['MethodB_35x35_Compile_Time'] = m35['Elapsed Time (s)'].values[0]
                row['MethodB_35x35_Execution_Time'] = m35['Total_T (us)'].values[0]
                row['MethodB_35x35_Fidelity'] = m35['Fidelity (DasAtom Model)'].values[0]
                row['MethodB_35x35_Move_Ops'] = m35['Num Movement Ops'].values[0]
            else:
                row['MethodB_35x35_Compile_Time'] = None
                row['MethodB_35x35_Execution_Time'] = None
                row['MethodB_35x35_Fidelity'] = None
                row['MethodB_35x35_Move_Ops'] = None
        
        results.append(row)
    
    # Create DataFrame
    df_result = pd.DataFrame(results)
    
    # Reorder columns for better readability
    column_order = [
        'Circuit',
        # Enola
        'Enola_Compile_Time', 'Enola_Execution_Time', 'Enola_Fidelity', 'Enola_Move_Ops',
        # DasAtom 11x11
        'DasAtom_11x11_Compile_Time', 'DasAtom_11x11_Execution_Time', 
        'DasAtom_11x11_Fidelity', 'DasAtom_11x11_Move_Ops',
        # DasAtom 35x35
        'DasAtom_35x35_Compile_Time', 'DasAtom_35x35_Execution_Time',
        'DasAtom_35x35_Fidelity', 'DasAtom_35x35_Move_Ops',
        # DasAtom 1.2xsqrtN
        'DasAtom_1.2xSqrtN_Compile_Time', 'DasAtom_1.2xSqrtN_Execution_Time',
        'DasAtom_1.2xSqrtN_Fidelity', 'DasAtom_1.2xSqrtN_Move_Ops',
        # Method B 11x11
        'MethodB_11x11_Compile_Time', 'MethodB_11x11_Execution_Time',
        'MethodB_11x11_Fidelity', 'MethodB_11x11_Move_Ops',
        # Method B 35x35
        'MethodB_35x35_Compile_Time', 'MethodB_35x35_Execution_Time',
        'MethodB_35x35_Fidelity', 'MethodB_35x35_Move_Ops',
    ]
    
    if not df_result.empty:
        df_result = df_result.reindex(columns=column_order)

    # Save to CSV
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df_result.to_csv(output_path, index=False)
    print(f"QFT comparison table saved to: {output_path}")
    print(f"\nTable dimensions: {df_result.shape[0]} circuits x {df_result.shape[1]} columns")
    print(f"\nFirst 5 rows:")
    print(df_result.head().to_string())
    
    return df_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="results",
                        help="Directory containing benchmark result CSVs (default: results)")
    parser.add_argument("--output", default=None,
                        help="Output CSV path (default: {results-dir}/qft_step5_comparison_full.csv)")
    args = parser.parse_args()
    output_path = args.output or os.path.join(args.results_dir, "qft_step5_comparison_full.csv")
    create_comparison_table(args.results_dir, output_path)
