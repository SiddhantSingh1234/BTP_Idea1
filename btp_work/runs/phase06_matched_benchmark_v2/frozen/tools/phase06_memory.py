"""Lossless, scoped execution-memory revision; scientific sources stay frozen.

Frozen JSON containers share read-only replay evidence through deepcopy. All
prefix values and their canonical fingerprints remain identical. Writers stream
the same JSON encoding, avoiding complete formatted strings in memory.
"""
from contextlib import contextmanager
from copy import deepcopy
import gc
import hashlib
import json
import math
from pathlib import Path
import sys


def immutable(*args, **kwargs):
    raise TypeError('Read-only Phase06 replay evidence')


class FrozenList(list):
    def __deepcopy__(self, memo):
        return self
    __setitem__ = __delitem__ = append = extend = insert = pop = remove = clear = sort = reverse = __iadd__ = __imul__ = immutable


class FrozenDict(dict):
    def __deepcopy__(self, memo):
        return self
    __setitem__ = __delitem__ = update = pop = popitem = clear = setdefault = __ior__ = immutable


class Freeze:
    def __init__(self):
        self.random_blocks = {}

    def __call__(self, value):
        if isinstance(value, (FrozenList, FrozenDict)):
            return value
        if isinstance(value, str):
            return sys.intern(value)
        if isinstance(value, dict):
            return FrozenDict((sys.intern(str(k)) if isinstance(k, str) else k, self(v)) for k, v in value.items())
        if isinstance(value, (list, tuple)):
            # MT19937 arrays recur with only the final index changed. Share
            # their immutable integer objects without changing any JSON value.
            if len(value) == 625 and all(type(x) is int for x in value):
                key = tuple(value[:624])
                block = self.random_blocks.setdefault(key, key)
                return FrozenList((*block, value[624]))
            return FrozenList(self(v) for v in value)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Nonfinite replay evidence cannot be shared')
        return value


def streaming_fingerprint(value):
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False)
    pending, size = [], 0
    for chunk in encoder.iterencode(value):
        pending.append(chunk)
        size += len(chunk)
        if size >= 65536:
            digest.update(''.join(pending).encode())
            pending.clear()
            size = 0
    if pending:
        digest.update(''.join(pending).encode())
    return digest.hexdigest()


def freeze_compilation(value):
    freeze = Freeze()
    for field in ['repair_boundaries', 'decisions', 'batches', 'assignment_records', 'route_prefix_records']:
        value[field] = freeze(value[field])
    return value


@contextmanager
def memory_scope():
    import implementation.repair.replay as replay_module
    import implementation.repair.search as search
    import implementation.repair.artifacts as artifacts
    import implementation.repair.evaluation as evaluation
    original_context = replay_module.ReplayContext
    original_hash = search.fingerprint
    original_write = artifacts.write
    original_safe = artifacts.safe
    original_evaluate_compilation = evaluation.evaluate_compilation
    replacements = []

    class MemoryContext(original_context):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.memory_freeze = Freeze()
        def route(self, *args, **kwargs):
            result = super().route(*args, **kwargs)
            boundary = self.boundaries[-1]
            boundary['prefix_state'] = self.memory_freeze(boundary['prefix_state'])
            return result

    def fingerprint(value):
        if isinstance(value, dict) and ('compilation' in value or 'repair_boundaries' in value):
            return streaming_fingerprint(value)
        return original_hash(value)

    def safe(value):
        if isinstance(value, (FrozenDict, FrozenList)):
            return value
        return original_safe(value)

    def write(path, value):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.tmp')
        with temporary.open('w', encoding='utf-8', newline='\n') as handle:
            encoder = json.JSONEncoder(indent=2, allow_nan=False)
            # writelines streams encoder chunks without allocating a full JSON
            # string; safe preserves the existing explicit nonfinite encoding.
            handle.writelines(encoder.iterencode(safe(value)))
            handle.write('\n')
        temporary.replace(path)

    # evaluate_compilation's event_audit is discarded by the original artifact
    # writer, and is not read by repair. Suppress only this optional audit,
    # retaining every validation, full schedule and final physical/error state.
    import types
    original_evaluator = original_evaluate_compilation.__globals__['evaluate']
    def no_audit(schedule):
        return original_evaluator(schedule, include_audit=False)
    namespace = dict(original_evaluate_compilation.__globals__)
    namespace['evaluate'] = no_audit
    compact_evaluation = types.FunctionType(original_evaluate_compilation.__code__, namespace,
        original_evaluate_compilation.__name__, original_evaluate_compilation.__defaults__)

    replay_module.ReplayContext = MemoryContext
    search.fingerprint = fingerprint
    artifacts.safe = safe
    artifacts.write = write
    evaluation.evaluate_compilation = compact_evaluation
    # Existing workers import artifact helpers directly. Redirect their write
    # alias too; write_bundle/save_result resolve artifacts.write dynamically.
    for name in ['phase06_comparison_worker']:
        module = sys.modules.get(name)
        if module is not None:
            replacements.append((module, module.write))
            module.write = write
    try:
        yield
    finally:
        for module, previous in replacements:
            module.write = previous
        replay_module.ReplayContext = original_context
        search.fingerprint = original_hash
        artifacts.safe = original_safe
        artifacts.write = original_write
        evaluation.evaluate_compilation = original_evaluate_compilation
        gc.collect()
