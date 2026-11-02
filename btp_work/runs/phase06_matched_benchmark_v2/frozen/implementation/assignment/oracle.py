"""Independent factorial tiny oracle; never used by the production solver."""
import itertools
import math


def enumerate_optimum(oriented, objective):
    m = len(oriented)
    s = len(oriented[0]) if m else 0
    if m > 6 or s > 8:
        raise ValueError('Tiny oracle only: m<=6, s<=8')
    best = None
    solutions = 0
    for columns in itertools.permutations(range(s), m):
        for orientations in itertools.product((0, 1), repeat=m):
            values = [oriented[row][col][ori] for row, (col, ori) in enumerate(zip(columns, orientations))]
            if not all(math.isfinite(x) for x in values):
                continue
            total, maximum = math.fsum(values), max(values, default=0.)
            key = (maximum, total) if objective == 'bottleneck_sum' else (total,)
            solutions += 1
            if best is None or key < best['objective']:
                best = {'objective': key, 'columns': columns, 'orientations': orientations}
    return None if best is None else {**best, 'feasible_oriented_assignments': solutions}
