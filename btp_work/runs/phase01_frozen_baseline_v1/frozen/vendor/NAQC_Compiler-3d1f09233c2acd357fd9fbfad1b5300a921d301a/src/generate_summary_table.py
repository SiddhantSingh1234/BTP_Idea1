import pandas as pd
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate summary table from benchmark CSVs")
    parser.add_argument("--csv-dir", type=str, required=True, help="Directory containing results CSVs")
    parser.add_argument("--dataset", type=str, default="qft_total", help="Dataset prefix (e.g., qft_total or tetris_ladder)")
    parser.add_argument("--method-a-file", type=str, default=None, help="Override Method A CSV filename")
    parser.add_argument("--method-b-file", type=str, default=None, help="Override Method B CSV filename")
    args = parser.parse_args()

    csv_dir = args.csv_dir
    dataset = args.dataset
    
    # Construct default filenames if not provided
    # Note: Benchmark runner output format: {dataset}_ladder_{variant}.csv
    # But for tetris run I used dataset="tetris_ladder", so file is tetris_ladder_ladder_...
    # I should be flexible.
    
    file_a = args.method_a_file or f"{dataset}_ladder_4_CoM_subset.csv"
    file_b = args.method_b_file or f"{dataset}_ladder_8_optimized_eviction.csv"
    file_das = f"dasatom_{dataset}_results.csv"

    # Load data
    try:
        path_a = os.path.join(csv_dir, file_a)
        path_b = os.path.join(csv_dir, file_b)
        path_das = os.path.join(csv_dir, file_das)
        
        print(f"Loading Method A: {path_a}")
        df_a = pd.read_csv(path_a)
        print(f"Loading Method B: {path_b}")
        df_b = pd.read_csv(path_b)
        print(f"Loading DasAtom: {path_das}")
        df_das = pd.read_csv(path_das)
    except Exception as e:
        print(f"Error loading CSVs: {e}")
        return

    # Normalize column names just in case
    # Num Qubit is standard
    
    # Sort key: Num Qubit then QASM File
    sort_cols = ['Num Qubit', 'QASM File']
    
    df_a = df_a.sort_values(sort_cols)
    df_b = df_b.sort_values(sort_cols)
    df_das = df_das.sort_values(sort_cols)

    # We want a joined view. 
    # Use Method A as base (assuming it completed everything).
    
    columns = ["Circuit", "Qubits", "Method A (Time s)", "Method B (Time s)", "DasAtom (Time s)", "Method A (Fid)", "Method B (Fid)", "DasAtom (Fid)"]
    results = []
    
    for _, row_a in df_a.iterrows():
        circuit = row_a['QASM File']
        qubits = row_a['Num Qubit']
        
        # Find corresponding rows
        row_b = df_b[df_b['QASM File'] == circuit]
        row_das = df_das[df_das['QASM File'] == circuit]
        
        res_row = [circuit, qubits]
        
        # Times
        res_row.append(f"{row_a['Elapsed Time (s)']:.3f}")
        res_row.append(f"{row_b['Elapsed Time (s)'].values[0]:.3f}" if not row_b.empty else "N/A")
        res_row.append(f"{row_das['Elapsed Time (s)'].values[0]:.3f}" if not row_das.empty else "N/A")
        
        # Fidelities
        res_row.append(f"{row_a['Fidelity (Realistic)']:.2e}")
        res_row.append(f"{row_b['Fidelity (Realistic)'].values[0]:.2e}" if not row_b.empty else "N/A")
        res_row.append(f"{row_das['Fidelity (Realistic)'].values[0]:.2e}" if not row_das.empty else "N/A")
        
        results.append(res_row)

    summary_df = pd.DataFrame(results, columns=columns)
    print(f"\n### {dataset} Performance Summary (11x11 Grid)\n")
    print(summary_df.to_markdown(index=False))
    
    # Also save to CSV
    out_file = os.path.join(csv_dir, f"summary_{dataset}.csv")
    summary_df.to_csv(out_file, index=False)
    print(f"\nSummary saved to {out_file}")

if __name__ == "__main__":
    main()
