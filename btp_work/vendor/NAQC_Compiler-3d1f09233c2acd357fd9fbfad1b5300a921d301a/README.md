Qiskit-style Neutral-Atom Compiler — Quick README

Overview
- This repository contains a neutral-atom-style compiler toolkit plus scripts to benchmark, plot, and visualize results.

Key files (purpose)
- `src/compiler_core.py`: core compiler implementation. Defines `CompilerOptions` and the `generate_hardware_instructions(...)` pipeline.
- `src/benchmark_runner.py`: runs the compiler over a folder of QASM circuits for multiple “ladder” variants and writes per-variant CSVs + hardware instruction logs.
- `src/final_plot.py`: makes per-feature line plots (and optional interactive HTML via Plotly) from CSV inputs. Supports plotting ladder results, legacy CSV sets, or both.
- `src/ladder_plot.py`: makes ladder boxplots and mean-by-variant plots from ladder CSVs.
- `src/generate_visualizations.py`: consumes instruction logs (`*_instructions.txt`) and generates per-circuit movement plots, heatmaps, and GIF animations, plus an HTML index.
- `src/dasatom_instruction_converter.py`: runs DasAtom’s own routing/embedding pipeline and converts its output into the same `*_instructions.txt` format used by our visualizers.

Prerequisites
- Python 3.8+ and a project virtual environment.
- Typical Python packages: `qiskit`, `numpy`, `pandas`, `scipy`, `matplotlib`, `plotly` (optional).

Setup (PowerShell)
```powershell
# Activate the repo virtualenv
.\.venv\Scripts\Activate.ps1

# Install required packages (if not already installed)
pip install -r requirements.txt
```

Running benchmarks (generate CSVs)
- `src/benchmark_runner.py`:
  - Reads `.qasm` files from `--folder`.
  - Runs all variants defined in `ladder_variants()` (filterable via `--variants`).
  - Writes CSVs into `results/{dataset}_ladder_rint{r_int}/`.
  - Writes instruction logs into `instruction_logs/{dataset}_ladder_rint{r_int}/{variant}/`.

Example
```powershell
python ./src/benchmark_runner.py --dataset tetris --folder ".\dasatom\DasAtom-main\Data\Q_Tetris\"
```

Plotting results

Example
```powershell
python ./src/final_plot.py --mode ladder --datasets tetris --output-dir .\plots\test_plot_tetris --csv-dir results/tetris_ladder_rint2
```

Example
```powershell
python ./src/ladder_plot.py --dataset qft --csv-dir .\results\qft_ladder_rint2\ --out-dir .\plots\test_qft_box_plot\
```

Variant configuration and toggles
- Ladder variants are defined inside `benchmark_runner.py` in the `ladder_variants()` function. Edit or add variants there by constructing `CompilerOptions(...)`.
- Notable toggles available on `CompilerOptions` in `compiler_core.py`:
  - `enable_rft_hungarian_bias` (bool): enables RFT-based future-bias in Hungarian assignment.
  - `rft_hungarian_bias_weight` (float): bias weight used when enabled.
  - `rft_hungarian_bias_max_time_dist` (int): max time distance considered for RFT bias.
  - `evicted_park_closest_to_partner` (bool): alternative placement heuristic for evicted qubits.

Files and outputs
- Bench CSVs (per variant): `results/{dataset}_ladder_rint{r_int}/{dataset}_ladder_{variant}.csv`
- Instruction logs (per circuit): `instruction_logs/{dataset}_ladder_rint{r_int}/{variant}/{circuit}_instructions.txt`
- Plots:
  - `src/ladder_plot.py`: PDFs written to `--out-dir`
  - `src/final_plot.py`: PDFs written to `--output-dir` and optional HTMLs to `{output-dir}/interactive/`

DasAtom series on line plots (Excel summary placement)
- To include a "DasAtom" series in `src/final_plot.py` line plots, place these files in the ladder results folders:
  - `results/qft_ladder_rint2/qft_summary.xlsx`
  - `results/tetris_ladder_rint2/tetris_summary.xlsx`

  `final_plot.py` looks for those files inside the `--csv-dir` folder it is given.

Input / Output directories
- Input circuits: `--folder` for `src/benchmark_runner.py` (must be a folder containing `.qasm` files).
- Output CSVs: always written under `results/{dataset}_ladder_rint{r_int}/` by `src/benchmark_runner.py`.
- Instruction logs: written under `instruction_logs/{dataset}_ladder_rint{r_int}/{variant}/` by `src/benchmark_runner.py`.

CLI Flags and Defaults (complete)

`src/benchmark_runner.py`
- `--folder` (str): folder containing `.qasm` files.
  - Default: `dasatom/DasAtom-main/Data/qiskit-bench/qft/qft_small`
- `--dataset` (str): dataset name used in output paths and filenames.
  - Default: `qft`
- `--limit` (int or None): limit number of `.qasm` files processed.
  - Default: `None` (process all)
- `--r-ints` (str or None): comma-separated list of `r_int` values (interaction radius) to sweep. Each value produces a separate `results/{dataset}_ladder_rint{r_int}/` folder.
  - Default: `None` (uses the script's built-in default of `2`)
- `--variants` (str or None): comma-separated list of variant names to run; runs all defined in `ladder_variants()` if omitted.
  - Default: `None`
- `--r-blk` (int): blockade/restriction radius used for compatibility checks.
  - Default: `4`
- `--grid-size` (int or None): override layout grid size (single integer N for an NxN grid).
  - Default: `None` (uses `R=C=15`)
- `--dynamic-grid` (flag): use `sqrt(n)xsqrt(n)` grid sized to each circuit's qubit count instead of a fixed grid.
  - Default: off

- Notable `CompilerOptions` toggles in `compiler_core.py` (defaults shown where set):
  - `enable_rft_hungarian_bias` (bool): default `False`. When `True`, biases Hungarian assignment using RFT future-partner info.
  - `rft_hungarian_bias_weight` (float): default `0.3`. Weight multiplier applied to the future-bias term.
  - `rft_hungarian_bias_max_time_dist` (int): default `3`. Maximum time distance (in future-partner steps) considered for bias.
  - `evicted_park_closest_to_partner` (bool): default `False`. When `True`, evicted qubits park at the idle spot closest to their future partner.
  - `assignment_mode` (enum `AssignmentMode`): default set in `CompilerOptions()`; common values are `HUNGARIAN`, `RANDOM`.
  - `idle_parking_mode` (enum `IdleParkingMode`): default set in `CompilerOptions()`; values include `GREEDY_NEAREST`, `RFT_GREEDY`, `RANDOM`.
  - `candidate_slots_mode` (enum `CandidateSlotsMode`): default in `CompilerOptions()`; controls how compatible slots are chosen.

Notes about flags vs. options
- CLI flags (like `--folder`, `--dataset`, `--limit`) control what files are processed and how many. The compiler behavior is controlled by `CompilerOptions` constructed in `ladder_variants()` inside `benchmark_runner.py` — modify or add variants there to change toggles and then re-run the runner to produce new CSVs.

`src/final_plot.py`
- `--csv-dir` (str): base directory used to locate CSVs and the optional `{dataset}_summary.xlsx`.
  - Default: `results/qft_ladder_rint2`
- `--mode` (str): what to plot.
  - Allowed: `legacy`, `ladder`, `both`
  - Default: `both`
- `--datasets` (str): which dataset(s) to plot.
  - Allowed: `qft`, `tetris`, `both`
  - Default: `both`
- `--output-dir` (str or None): output directory.
  - Default: `plots/plots_ladder` when `--mode ladder`, otherwise `plots/plots_right_filled_dynamic_layout2`

`src/ladder_plot.py`
- `--dataset` (str): dataset prefix used to find `{dataset}_ladder_*.csv`.
  - Required (no default)
- `--csv-dir` (str): directory containing ladder CSVs.
  - Default: `results/qft_ladder_rint2`
- `--out-dir` (str or None): output directory for plot PDFs.
  - Default: `plots/{dataset}_ladder`

`src/generate_visualizations.py`
- `--qasm-folder` (str): folder containing the `.qasm` files (used to render circuit diagrams).
  - Default: `../dasatom/DasAtom-main/Data/qiskit-bench/qft/qft_small`
- `--instructions-dir` (str): directory containing `*_instructions.txt` files.
  - Default: `instruction_logs`
- `--output-dir` (str): base directory to write generated images, GIFs, and the HTML index.
  - Default: `visualization_outputs`

Example
```powershell
python ./src/generate_visualizations.py --instructions-dir instruction_logs --output-dir visualization_outputs --qasm-folder "\dasatom\DasAtom-main\Data\qiskit-bench\qft\qft_small"
```

`src/dasatom_instruction_converter.py`
- `--qasm-folder` (str): folder containing `.qasm` files.
  - Default: `../dasatom/DasAtom-main/Data/qiskit-bench/qft/qft_small`
- `--output-dir` (str): output directory for `*_instructions.txt` files.
  - Default: `dasatom_instruction_logs`

Example
```powershell
python ./src/dasatom_instruction_converter.py --qasm-folder ".\dasatom\DasAtom-main\Data\Q_Tetris\" --output-dir dasatom_instruction_logs
```

Examples (explicit csv-dir and out-dir)
```powershell
# Plot ladder CSVs that live in ./results_csvs and write output into ./plots_qft_ladder
python .\src\ladder_plot.py --dataset qft --csv-dir .\results_csvs --out-dir .\plots_qft_ladder

# Generate final plots (both modes) reading CSVs from ./results_csvs and saving to ./plots_all
python .\src\final_plot.py --csv-dir .\results_csvs --mode both --datasets both --output-dir .\plots_all
```

Troubleshooting
- If plots do not show a variant, confirm the corresponding `{dataset}_ladder_{variant}.csv` exists.

Next steps
- To generate plots, first run `benchmark_runner.py` to produce the CSV files, then run the plotting scripts above.


## QFT Scaling Analysis Plot

To generate per-variant PDF plots comparing different grid configurations (11x11 / 20x20 / 35x35) of DasAtom and Our Approach across QFT step-5 circuits, use:

```powershell
python .\src\qft_grid_comparison_plot_final.py --results-dir .\results --plots-dir .\plots
```

CLI flags:
- `--results-dir` (default `results`): directory containing the per-variant CSV folders (e.g. `qft_step5_ladder_rint2/dasatom_qft_step5_results.csv`).
- `--plots-dir` (default `plots`): directory under which `{variant}/qft_grid_comparison_OPTIMIZED/qft_*.pdf` files are written.
- `--variants` (default `9_perimeter_staging 10_asap_packager 11_auto_tuning`): variant subdirectory names to process.

## Comprehensive Tables

To generate the fully formatted comparative paper tables covering Enola (static dataset) against the DasAtom implementations (11x11, 35x35) and Method B:

```powershell
python .\src\qft_comparison_table.py --results-dir .\results
python .\src\qtetris_comparison_table.py --results-dir .\results
```

CLI flags:
- `--results-dir` (default `results`): directory containing the per-variant CSV folders. The QFT script writes `{results-dir}/qft_step5_comparison_full.csv`; the Q_Tetris script writes `{results-dir}/{variant}/qtetris_comparison_full.csv` for each variant.
- `--output` (QFT only): override the output CSV path.
- `--variants` (Q_Tetris only): variant subdirectory names to process.

These commands parse `qtetris_enola_results.csv` and the ladder variants to spit out the master comparison CSVs formatted to the standard paper requirements.

