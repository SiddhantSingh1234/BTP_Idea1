"""Record paper Table II values as reference, separate from fresh measurements."""
import csv
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
DATA='''4mod5-v1_22 0.051 0.090 0.894 0.023 0.946 0.944 0.946 0.942 0 2 0 5
adr4_197 5.145 1.454 76.358 1.432 5.0e-4 3.0e-4 5.0e-4 3.0e-4 55 470 55 459
alu-v0_27 0.101 0.069 0.974 0.027 0.918 0.909 0.918 0.908 0 9 0 10
bv_n16 0.145 0.063 2.842 0.042 0.926 0.919 0.926 0.920 2 9 2 8
cm152a_212 0.921 0.394 7.602 0.484 0.069 0.058 0.069 0.060 6 159 6 126
dc1_220 2.300 0.622 23.663 0.757 0.015 0.012 0.015 0.012 23 262 23 264
ising_model_16 0.123 0.085 0.723 0.047 0.471 0.459 0.471 0.465 0 22 0 9
misex1_241 26.977 1.921 643.382 2.435 2.6e-5 1.3e-5 2.6e-5 1.2e-5 52 689 52 710
qft_16 8.537 0.093 199.612 0.095 0.290 0.285 0.290 0.290 34 41 34 27
qv_n16_d5 91.010 0.037 2394.494 0.028 0.542 0.538 0.542 0.544 10 14 10 4
rd53_251 0.760 0.534 6.475 0.604 0.059 0.050 0.059 0.049 15 153 15 166
rd73_252 5.354 1.859 66.999 2.211 8.5e-6 4.1e-6 8.5e-6 4.1e-6 83 704 83 702
square_root_7 227.547 2.496 4571.890 2.808 1.7e-7 6.9e-8 1.7e-7 6.0e-8 106 909 106 866
sym6_145 2.560 1.310 18.933 1.855 1.9e-4 1.1e-4 1.9e-4 1.1e-4 40 504 40 577
z4_268 3.545 1.031 52.019 1.519 0.001 7.3e-4 0.001 7.5e-4 43 441 43 412'''


def main():
    out=WORK/'reports/phase_01/published_targets.csv'
    if out.exists():
        raise SystemExit('Reference ledger already exists')
    rows=[]
    for line in DATA.splitlines():
        name,*values=line.split()
        assert len(values)==12
        for grid_index,grid in enumerate([11,35]):
            for method_index,method in enumerate(['dasatom','rft_paper_unknown_variant']):
                offset=2*grid_index+method_index
                rows.append(dict(family='tableII',circuit=name,grid=grid,method=method,
                    compile_seconds=values[offset],fidelity=values[4+offset],movement_batches=values[8+offset],
                    source='RFT manuscript PDF page 6 Table II',record_kind='published_reference_not_new_measurement',
                    source_revision='unknown',numeric_verification='transcribed_from_local_PDF_text'))
    for n in range(5,61,5):
        for grid in [11,20,35]:
            for method in ['dasatom','rft_paper_unknown_variant']:
                rows.append(dict(family='fig4_qft',circuit=f'qft_{n}',grid=grid,method=method,
                    compile_seconds=None,fidelity=None,movement_batches=None,
                    source='RFT manuscript PDF page 6 Figure 4; sampled sizes supported by current plot filter',
                    record_kind='published_target_graph_values_not_digitized',source_revision='unknown',
                    numeric_verification='no_exact_graph_values_claimed'))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f'Saved {len(rows)} published target rows separately from current-source results')


if __name__=='__main__':
    main()
