"""Rectangular exact sum / (maximum, sum) matching with truly forbidden edges."""
from dataclasses import dataclass
import math
import time


class AssignmentInfeasible(ValueError):
    pass


@dataclass(frozen=True)
class Matching:
    columns: tuple
    maximum: float
    total: float
    threshold: float | None
    feasibility_calls: int
    seconds: float


def matrix(values):
    rows = tuple(tuple(float(x) for x in row) for row in values)
    if rows and any(len(row) != len(rows[0]) for row in rows):
        raise ValueError('Ragged matrix')
    if any(math.isnan(x) or x == -math.inf for row in rows for x in row):
        raise ValueError('NaN/negative infinity is not a cost')
    return rows


def covering_matching(costs, threshold=math.inf):
    """Deterministic BFS augmenting paths; forbidden +inf edges never enter."""
    m = len(costs)
    s = len(costs[0]) if m else 0
    if s < m:
        return None
    owners = [-1] * s
    chosen = [-1] * m
    for start in range(m):
        queue = [start]
        seen_rows = {start}
        parent_column = {}
        found = None
        for row in queue:
            for col in range(s):
                value = costs[row][col]
                if col in parent_column or not math.isfinite(value) or value > threshold:
                    continue
                parent_column[col] = row
                if owners[col] == -1:
                    found = col
                    break
                other = owners[col]
                if other not in seen_rows:
                    seen_rows.add(other)
                    queue.append(other)
            if found is not None:
                break
        if found is None:
            return None
        col = found
        while col != -1:
            row = parent_column[col]
            old = chosen[row]
            owners[col] = row
            chosen[row] = col
            col = old
    return tuple(chosen)


def minimum_sum(costs):
    """Rectangular shortest-augmenting-path Hungarian, O(m^2*s), O(m+s) work."""
    m = len(costs)
    s = len(costs[0]) if m else 0
    if s < m:
        raise AssignmentInfeasible('Fewer columns than real rows')
    u, v = [0.] * (m + 1), [0.] * (s + 1)
    owner, way = [0] * (s + 1), [0] * (s + 1)
    for row in range(1, m + 1):
        owner[0] = row
        col = 0
        minimum = [math.inf] * (s + 1)
        used = [False] * (s + 1)
        while True:
            used[col] = True
            active = owner[col]
            delta, next_col = math.inf, -1
            for j in range(1, s + 1):
                if used[j]:
                    continue
                reduced = costs[active - 1][j - 1] - u[active] - v[j]
                if reduced < minimum[j]:
                    minimum[j], way[j] = reduced, col
                if minimum[j] < delta:
                    delta, next_col = minimum[j], j
            if not math.isfinite(delta):
                raise AssignmentInfeasible('Hall condition fails on legal edges')
            for j in range(s + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            col = next_col
            if owner[col] == 0:
                break
        while True:
            previous = way[col]
            owner[col] = owner[previous]
            col = previous
            if col == 0:
                break
    chosen = [-1] * m
    for j in range(1, s + 1):
        if owner[j]:
            chosen[owner[j] - 1] = j - 1
    if any(col < 0 or not math.isfinite(costs[row][col]) for row, col in enumerate(chosen)):
        raise AssignmentInfeasible('No complete legal assignment')
    return tuple(chosen)


def solve(values, objective='bottleneck_sum'):
    started = time.perf_counter()
    costs = matrix(values)
    if objective not in ('sum', 'bottleneck_sum'):
        raise ValueError('Unknown frozen-matrix objective')
    if not costs:
        return Matching((), 0., 0., None, 0, time.perf_counter() - started)
    threshold, calls = None, 0
    allowed = costs
    if objective == 'bottleneck_sum':
        unique = sorted({x for row in costs for x in row if math.isfinite(x)})
        if not unique:
            raise AssignmentInfeasible('No legal finite edges')
        low, high = 0, len(unique) - 1
        calls += 1
        if covering_matching(costs, unique[high]) is None:
            raise AssignmentInfeasible('No matching covers all real rows')
        while low < high:
            mid = (low + high) // 2
            calls += 1
            if covering_matching(costs, unique[mid]) is None:
                low = mid + 1
            else:
                high = mid
        threshold = unique[low]
        allowed = tuple(tuple(x if x <= threshold else math.inf for x in row) for row in costs)
    columns = minimum_sum(allowed)
    chosen = [costs[row][col] for row, col in enumerate(columns)]
    return Matching(columns, max(chosen), math.fsum(chosen), threshold, calls,
                    time.perf_counter() - started)
