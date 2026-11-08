"""E2: How costly is recognising TU?

Generate inputs: python3 e2.py generate
Check independently: python3 e2.py check
Run benchmark: python3 e2.py run --cmr /path/to/cmr-tu
Inputs: data/manifest.json and family JSON files. Outputs: results/<run>/.
Nothing runs without an explicit subcommand.

Standard-library Python 3.10+. CMR is an external executable, not a pip package.
See README.md before running checks or benchmarks.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import itertools as it
import json
from pathlib import Path
import platform
import random
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / 'data'


# ---------------------------------------- dataset storage

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_dataset(data, directory, force=False):
    """One file per family plus a small manifest; preserve record order and IDs."""
    directory.mkdir(parents=True, exist_ok=True)
    names = list(data['counts'])
    targets = [directory / f'{name}.json' for name in names] + [directory / 'manifest.json']
    if not force and any(path.exists() for path in targets):
        raise SystemExit('Dataset exists; use --force to overwrite intentionally.')
    files = []
    for name in names:
        records = [x for x in data['matrices'] if x['family'] == name]
        # Keep each matrix row on one line instead of expanding every scalar.
        entries = []
        for record in records:
            metadata = {k: v for k, v in record.items() if k != 'matrix'}
            text = json.dumps(metadata, indent=2)[:-2]
            rows = ',\n'.join('    ' + json.dumps(row) for row in record['matrix'])
            entries.append(text + ',\n  "matrix": [\n' + rows + '\n  ]\n}')
        path = directory / f'{name}.json'
        path.write_text('{\n  "family": ' + json.dumps(name) + ',\n  "matrices": [\n' +
                        ',\n'.join(entries) + '\n  ]\n}\n')
        files.append(dict(path=path.name, family=name, count=len(records), sha256=digest(path)))
    manifest = {k: v for k, v in data.items() if k != 'matrices'}
    manifest['schema_version'] = 2
    manifest['files'] = files
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def load_dataset(path):
    """Read a dataset directory/manifest, retaining legacy combined-file support."""
    manifest_path = path / 'manifest.json' if path.is_dir() else path
    data = json.loads(manifest_path.read_text())
    if 'files' not in data:
        return data
    records = []
    for entry in data['files']:
        source = manifest_path.parent / entry['path']
        if digest(source) != entry['sha256']:
            raise ValueError(f'Dataset hash mismatch: {source}')
        part = json.loads(source.read_text())
        if len(part['matrices']) != entry['count'] or any(
                x['family'] != entry['family'] for x in part['matrices']):
            raise ValueError(f'Dataset family/count mismatch: {source}')
        records.extend(part['matrices'])
    return dict(data, matrices=records)


def input_hashes(path):
    manifest_path = path / 'manifest.json' if path.is_dir() else path
    data = json.loads(manifest_path.read_text())
    return {manifest_path.name: digest(manifest_path), **{
        entry['path']: digest(manifest_path.parent / entry['path'])
        for entry in data.get('files', [])}}


# ---------------------------------------- instance generation

def cycle(n):
    return [[int(j == i or j == (i + 1) % n) for j in range(n)] for i in range(n)]


def blocks(parts):
    m = sum(len(a) for a in parts)
    n = sum(len(a[0]) for a in parts)
    out = [[0] * n for _ in range(m)]
    r = c = 0
    for a in parts:
        for i, row in enumerate(a):
            out[r + i][c:c + len(row)] = row
        r += len(a)
        c += len(a[0])
    return out


def generate(seed):
    records = []

    def add(family, a, n, expected, parameters=None, witness=None,
            parent=None, transform=None):
        record = dict(id=f'{family}_{sum(x["family"] == family for x in records):03d}',
                      group='transformed' if parent else 'main', family=family,
                      rows=len(a), columns=n, nonzeros=sum(v != 0 for row in a for v in row),
                      expected_tu=expected, parameters=parameters or {},
                      matrix=a, parent_id=parent, transformation=transform,
                      known_witness=witness)
        records.append(record)
        return record

    for n in [4, 6, 8, 10, 12, 16, 24, 40, 80, 160]:
        add('even_cycle', cycle(n), n, True, {'order': n})
    for n in [3, 5, 7, 9, 11, 15, 23, 39, 79, 159]:
        add('odd_cycle', cycle(n), n, False, {'order': n}, {'rows': list(range(n)), 'columns': list(range(n)), 'absolute_determinant': 2})
    for n in [8, 12, 20, 40, 80, 160]:
        for p in [0.2, 0.6]:
            for draw in range(10):
                s = seed + 100000 * n + int(p * 100) * 100 + draw
                rng = random.Random(s)
                edges = [(u, v) for u in range(n // 2) for v in range(n // 2, n)
                         if rng.random() < p]
                a = [[int(j in (u, v)) for j in range(n)] for u, v in edges]
                add('bipartite', a, n, True, {'vertices': n, 'partition_boundary': n // 2, 'p': p, 'draw': draw,
                     'seed': s, 'edges': edges})
    for n in [4, 6, 8, 10, 16, 32]:
        for kind in ['short', 'long']:
            for draw in range(10):
                s = seed + 20000000 + 10000 * n + 100 * (kind == 'long') + draw
                rng = random.Random(s)
                intervals = []
                a = [[0] * n for _ in range(n)]
                for j in range(n):
                    low, high = (1, max(1, n // 4)) if kind == 'short' else ((n + 1) // 2, n)
                    length = rng.randint(low, high)
                    start = rng.randrange(n - length + 1)
                    intervals.append([start, start + length])
                    for i in range(start, start + length):
                        a[i][j] = 1
                add('interval', a, n, True, {'order': n, 'length_class': kind, 'draw': draw, 'seed': s,
                     'intervals_half_open': intervals})
    for n in [7, 11, 19, 35, 67, 131]:
        add('embedded_triangle', blocks([cycle(3), cycle(n - 3)]), n, False,
            {'order': n},
            {'rows': [0, 1, 2], 'columns': [0, 1, 2], 'absolute_determinant': 2})
    for n in [8, 12, 16, 24, 32, 48, 64, 96]:
        for count in [1, 2, 4]:
            if n % count == 0 and n // count >= 4 and n // count % 2 == 0:
                add('block_cycles', blocks([cycle(n // count) for _ in range(count)]), n,
                    True, {'order': n, 'blocks': count, 'block_order': n // count})
    controls = [
        ('zero_1', [[0]], 1, True), ('zero_rect', [[0]*3 for _ in range(2)], 3, True),
        ('identity_1', [[1]], 1, True), ('negative_identity_1', [[-1]], 1, True),
        ('identity_2', [[1, 0], [0, 1]], 2, True),
        ('identity_4', [[int(i == j) for j in range(4)] for i in range(4)], 4, True),
        ('signed_identity', [[1, 0], [0, -1]], 2, True),
        ('all_ones', [[1]*3 for _ in range(2)], 3, True),
        ('one_row', [[1, -1, 0, 1]], 4, True),
        ('entry_two', [[2]], 1, False), ('entry_minus_two', [[-2]], 1, False),
        ('signed_det_two', [[1, 1], [1, -1]], 2, False)]
    for name, a, n, expected in controls:
        witness = None if expected else {'rows': list(range(len(a))),
                    'columns': list(range(n)), 'absolute_determinant': 2}
        add('control', a, n, expected,
            {'name': name}, witness)
    selected = []
    for family in ['bipartite', 'interval', 'embedded_triangle', 'block_cycles']:
        candidates = [x for x in records if x['family'] == family]
        selected.extend([candidates[0], candidates[len(candidates)//2]])
    for index, base in enumerate(selected):
        for variant in ['transpose', 'permute_1', 'permute_2', 'signs', 'permute_signs']:
            rng = random.Random(seed + 90000000 + 100 * index + len(records))
            m, n = base['rows'], base['columns']
            rp, cp = list(range(m)), list(range(n))
            rs, cs = [1]*m, [1]*n
            if variant.startswith('permute'):
                rng.shuffle(rp)
                rng.shuffle(cp)
            if variant in ['signs', 'permute_signs']:
                rs = [rng.choice([-1, 1]) for _ in rp]
                cs = [rng.choice([-1, 1]) for _ in cp]
            a = [[base['matrix'][r][c] * rs[i] * cs[j] for j, c in enumerate(cp)]
                 for i, r in enumerate(rp)]
            witness = base['known_witness']
            if witness:
                witness = {'rows': [rp.index(r) for r in witness['rows']],
                           'columns': [cp.index(c) for c in witness['columns']],
                           'absolute_determinant': witness['absolute_determinant']}
            if variant == 'transpose':
                a = [[base['matrix'][r][c] for r in range(m)] for c in range(n)]
                m, n = n, m
                if witness:
                    witness = dict(rows=witness['columns'], columns=witness['rows'],
                                   absolute_determinant=witness['absolute_determinant'])
            add('transformed', a, n, base['expected_tu'],
                {'variant': variant, 'row_order': rp, 'column_order': cp,
                 'row_signs': rs, 'column_signs': cs}, witness, base['id'], variant)
    return {'schema_version': 1, 'master_seed': seed, 'indexing': 'zero-based',
            'counts': dict(Counter(x['family'] for x in records)),
            'description': 'Inputs and mathematical labels only; no recognition results.', 'matrices': records}


# ---------------------------------------- exact recognition

def determinant(a):
    """Bareiss elimination with exact Python integers and row pivoting."""
    a = [row[:] for row in a]
    n, sign, previous = len(a), 1, 1
    if n == 0:
        return 1
    for k in range(n - 1):
        pivot_row = next((i for i in range(k, n) if a[i][k]), None)
        if pivot_row is None:
            return 0
        if pivot_row != k:
            a[k], a[pivot_row] = a[pivot_row], a[k]
            sign = -sign
        pivot = a[k][k]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                numerator = a[i][j]*pivot - a[i][k]*a[k][j]
                if numerator % previous:
                    raise ArithmeticError('Non-exact Bareiss division')
                a[i][j] = numerator // previous
            a[i][k] = 0
        previous = pivot
    return sign * a[-1][-1]


def recognise(a, n, method):
    counters = dict(minors_checked=0, subsets_checked=0, signings_checked=0)
    for i, row in enumerate(a):
        for j, value in enumerate(row):
            if value not in (-1, 0, 1):
                return dict(decision=False, witness={'rows': [i], 'columns': [j], 'determinant': value}, **counters)
    m = len(a)
    if method == 'brute':
        for k in range(1, min(m, n) + 1):
            for rows in it.combinations(range(m), k):
                for cols in it.combinations(range(n), k):
                    d = determinant([[a[i][j] for j in cols] for i in rows])
                    counters['minors_checked'] += 1
                    if abs(d) > 1:
                        return dict(decision=False, witness=dict(rows=rows, columns=cols, determinant=d), **counters)
    else:
        transposed = m > n
        if transposed:
            a = [[a[i][j] for i in range(m)] for j in range(n)]
            m, n = n, m
        for k in range(1, m + 1):
            for rows in it.combinations(range(m), k):
                counters['subsets_checked'] += 1
                # Global negation is symmetric, so fix the first sign to +1.
                for tail in it.product((-1, 1), repeat=k - 1):
                    signs = (1,) + tail
                    counters['signings_checked'] += 1
                    if all(abs(sum(s*a[i][j] for s, i in zip(signs, rows))) <= 1 for j in range(n)):
                        break
                else:
                    return dict(decision=False, witness=dict(unsigned_subset=rows,
                                subset_axis='columns' if transposed else 'rows'), **counters)
    return dict(decision=True, witness=None, **counters)


# ---------------------------------------- independent checks

def leibniz(a):
    """Independent tiny determinant reference for the user's correctness suite."""
    total = 0
    for perm in it.permutations(range(len(a))):
        inversions = sum(perm[i] > perm[j] for i in range(len(a))
                         for j in range(i + 1, len(a)))
        product = (-1) ** inversions
        for i, j in enumerate(perm):
            product *= a[i][j]
        total += product
    return total


def verify_result(record, method, result):
    """Check returned negative Python certificates outside measured execution."""
    if result.get('status') != 'ok' or result['decision'] or method == 'cmr':
        return
    a, w = record['matrix'], result['witness']
    if 'rows' in w:
        assert abs(determinant([[a[i][j] for j in w['columns']] for i in w['rows']])) > 1
    else:
        if w['subset_axis'] == 'columns':
            a = [[a[i][j] for i in range(record['rows'])] for j in range(record['columns'])]
        rows = w['unsigned_subset']
        for signs in it.product((-1, 1), repeat=len(rows)):
            assert any(abs(sum(s*a[i][j] for s, i in zip(signs, rows))) > 1
                       for j in range(len(a[0])))


def validate(data):
    """Dataset integrity/construction checks, not a general TU recognition run."""
    records = data['matrices']
    by_id = {x['id']: x for x in records}
    if len(by_id) != len(records):
        raise ValueError('Duplicate IDs')
    for x in records:
        a, m, n = x['matrix'], x['rows'], x['columns']
        assert len(a) == m and all(len(row) == n for row in a), x['id']
        assert all(type(v) is int for row in a for v in row), x['id']
        assert x['nonzeros'] == sum(v != 0 for row in a for v in row), x['id']
        p, f = x['parameters'], x['family']
        if f in ('even_cycle', 'odd_cycle'):
            assert a == cycle(n) and (n % 2 == 0) == x['expected_tu']
        elif f == 'bipartite':
            edges = []
            for row in a:
                ends = [j for j, v in enumerate(row) if v]
                assert len(ends) == 2 and all(row[j] == 1 for j in ends)
                assert ends[0] < p['partition_boundary'] <= ends[1]
                edges.append(ends)
            assert edges == p['edges']
        elif f == 'interval':
            for j, (start, stop) in enumerate(p['intervals_half_open']):
                assert 0 <= start < stop <= m
                assert [a[i][j] for i in range(m)] == [int(start <= i < stop) for i in range(m)]
        elif f == 'embedded_triangle':
            assert a == blocks([cycle(3), cycle(n - 3)])
        elif f == 'block_cycles':
            assert a == blocks([cycle(p['block_order']) for _ in range(p['blocks'])])
        elif f == 'transformed':
            base = by_id[x['parent_id']]
            if x['transformation'] == 'transpose':
                expected = [[base['matrix'][r][c] for r in range(base['rows'])]
                            for c in range(base['columns'])]
            else:
                expected = [[base['matrix'][r][c]*p['row_signs'][i]*p['column_signs'][j]
                             for j, c in enumerate(p['column_order'])]
                            for i, r in enumerate(p['row_order'])]
            assert a == expected and x['expected_tu'] == base['expected_tu']
        w = x['known_witness']
        if w:
            d = determinant([[a[i][j] for j in w['columns']] for i in w['rows']])
            assert abs(d) == w['absolute_determinant'] > 1, x['id']
    return Counter(x['family'] for x in records)


# ---------------------------------------- timed execution

def invoke(record, method, limit, cmr):
    a, n = record['matrix'], record['columns']
    if method == 'cmr':
        command = [cmr, '-', '--algo', 'decomposition', '--stats', '--time-limit', str(limit)]
        payload = f'{len(a)} {n}\n' + '\n'.join(' '.join(map(str, row)) for row in a) + '\n'
    else:
        command = [sys.executable, str(Path(__file__).resolve()), '_worker', method]
        payload = json.dumps({'matrix': a, 'columns': n})
    start = time.perf_counter()
    try:
        completed = subprocess.run(command, input=payload, text=True, capture_output=True, timeout=limit)
    except subprocess.TimeoutExpired:
        return dict(status='timeout', decision=None, wall_seconds=time.perf_counter()-start)
    wall = time.perf_counter() - start
    if method == 'cmr':
        output = completed.stdout.strip()
        details = dict(stdout=completed.stdout, stderr=completed.stderr, returncode=completed.returncode)
        if 'Time limit exceeded' in completed.stderr:
            return dict(status='timeout', decision=None, wall_seconds=wall, **details)
        decision = {'Matrix IS totally unimodular.': True,
                    'Matrix IS NOT totally unimodular.': False}.get(output)
        # CMR 1.4 reports the out-of-range-entry fast rejection on stderr.
        entry = re.search(r'Matrix is NOT totally unimodular since it is not ternary: '
                          r'entry at row (\d+), column (\d+) is (-?\d+)\.', completed.stderr)
        if entry and not output:
            r, c, value = map(int, entry.groups())
            if 1 <= r <= len(a) and 1 <= c <= n and a[r-1][c-1] == value and abs(value) > 1:
                decision = False
        status = 'ok' if completed.returncode == 0 and decision is not None else 'error'
        return dict(status=status, decision=decision, wall_seconds=wall, **details)
    if completed.returncode:
        return dict(status='error', decision=None, wall_seconds=wall, stderr=completed.stderr)
    result = json.loads(completed.stdout)
    return dict(status='ok', wall_seconds=wall, **result)


def benchmark(args, records):
    cmr = shutil.which(args.cmr)
    if 'cmr' in args.methods and cmr is None:
        raise SystemExit('CMR not found. Supply --cmr /absolute/path/to/cmr-tu or select --methods brute gh.')
    selected = [x for x in records if (not args.family or x['family'] in args.family)
                and (not args.ids or x['id'] in args.ids)
                and (args.max_dimension is None or max(x['rows'], x['columns']) <= args.max_dimension)]
    if args.take:
        selected = selected[:args.take]
    if not selected:
        raise SystemExit('No matching inputs')
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    # A fresh directory prevents accidentally mixing different runs.
    raw = out / 'measurements.jsonl'
    if raw.exists() or (out / 'results.csv').exists():
        raise SystemExit('Output already contains measurements. Choose a new --output directory.')
    metadata = dict(started_utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
                    platform=platform.platform(), machine=platform.machine(), processor=platform.processor(),
                    source_sha256=digest(__file__), input_sha256=input_hashes(args.data), cmr_path=cmr,
                    cmr_binary_sha256=digest(cmr) if cmr else None, arguments=vars(args).copy(),
                    selected_ids=[x['id'] for x in selected],
                    timing='wall includes subprocess startup, input parsing and output; Python algorithm_seconds excludes these',
                    cmr_build_note=args.cmr_build_note)
    metadata['arguments'] = {k: str(v) if isinstance(v, Path) else v for k, v in metadata['arguments'].items()}
    (out / 'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    fields = ['instance_id', 'family', 'group', 'parent_id', 'rows', 'columns', 'nonzeros',
              'expected_tu', 'method', 'repetition', 'status', 'decision', 'wall_seconds',
              'algorithm_seconds', 'minors_checked', 'subsets_checked', 'signings_checked']
    rng = random.Random(args.order_seed)
    with raw.open('w') as jf, (out / 'results.csv').open('w', newline='') as cf:
        writer = csv.DictWriter(cf, fields, extrasaction='ignore')
        writer.writeheader()
        for x in selected:
            for repeat in range(args.repeats):
                methods = args.methods[:]
                rng.shuffle(methods)
                for method in methods:
                    result = invoke(x, method, args.time_limit, cmr)
                    if result['status'] == 'ok' and result['decision'] != x['expected_tu']:
                        result['status'] = 'incorrect'
                    row = dict(instance_id=x['id'], **{k: x[k] for k in
                               ['family', 'group', 'parent_id', 'rows', 'columns', 'nonzeros', 'expected_tu']},
                               method=method, repetition=repeat + 1, **result)
                    jf.write(json.dumps(row)+'\n'); jf.flush()
                    writer.writerow(row); cf.flush()
                    verify_result(x, method, result)
                    print(x['id'], method, repeat + 1, result['status'], flush=True)
                    if result['status'] in ['error', 'incorrect']:
                        raise SystemExit('Stopped on failure; inspect measurements.jsonl. No failed result is silently excluded.')
    metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
    metadata['results_sha256'] = digest(out / 'results.csv')
    (out / 'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')


# ---------------------------------------- command line

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    gen = sub.add_parser('generate', help='Write inputs only; no recognisers run')
    gen.add_argument('--seed', type=int, default=20261108)
    gen.add_argument('--data', type=Path, default=DEFAULT_DATA)
    gen.add_argument('--force', action='store_true')
    check = sub.add_parser('check', help='Run dataset validation and exhaustive small-matrix correctness checks')
    check.add_argument('--data', type=Path, default=DEFAULT_DATA)
    check.add_argument('--cmr', default='cmr-tu')
    check.add_argument('--with-cmr', action='store_true')
    run = sub.add_parser('run', help='Run user-selected benchmarks and save measurements')
    run.add_argument('--data', type=Path, default=DEFAULT_DATA)
    run.add_argument('--output', type=Path, default=HERE / 'results' / datetime.now().strftime('run-%Y%m%d-%H%M%S'))
    run.add_argument('--methods', nargs='+', choices=['brute', 'gh', 'cmr'], default=['brute', 'gh', 'cmr'])
    run.add_argument('--cmr', default='cmr-tu')
    run.add_argument('--cmr-build-note', default='Not supplied; record CMR commit/compiler/Release configuration before final run.')
    run.add_argument('--family', nargs='+')
    run.add_argument('--ids', nargs='+')
    run.add_argument('--max-dimension', type=int)
    run.add_argument('--take', type=int)
    run.add_argument('--repeats', type=int, default=3)
    run.add_argument('--time-limit', type=float, default=5)
    run.add_argument('--order-seed', type=int, default=20261108)
    worker = sub.add_parser('_worker', help=argparse.SUPPRESS)
    worker.add_argument('method', choices=['brute', 'gh'])
    args = parser.parse_args()
    if args.command == '_worker':
        data = json.load(sys.stdin)
        start = time.perf_counter()
        result = recognise(data['matrix'], data['columns'], args.method)
        result['algorithm_seconds'] = time.perf_counter() - start
        print(json.dumps(result))
    elif args.command == 'generate':
        data = generate(args.seed)
        write_dataset(data, args.data, args.force)
        print('Generated inputs only:', len(data['matrices']), data['counts'])
    elif args.command == 'check':
        data = load_dataset(args.data)
        print('Dataset construction checks:', dict(validate(data)))
        cmr = shutil.which(args.cmr) if args.with_cmr else None
        if args.with_cmr and not cmr:
            raise SystemExit('CMR not found')
        for values in it.product((0, 1), repeat=9):
            a = [list(values[3*i:3*i+3]) for i in range(3)]
            expected = all(abs(leibniz([[a[i][j] for j in cols] for i in rows])) <= 1
                           for k in range(1, 4)
                           for rows in it.combinations(range(3), k)
                           for cols in it.combinations(range(3), k))
            assert recognise(a, 3, 'brute')['decision'] == expected, values
            assert recognise(a, 3, 'gh')['decision'] == expected, values
            if cmr:
                result = invoke({'matrix': a, 'columns': 3}, 'cmr', 5, cmr)
                assert result['status'] == 'ok' and result['decision'] == expected, (values, result)
        for x in data['matrices']:
            if x['family'] == 'control':
                for method in ['brute', 'gh'] + (['cmr'] if cmr else []):
                    result = invoke(x, method, 5, cmr)
                    assert result['status'] == 'ok' and result['decision'] == x['expected_tu'], (x['id'], method, result)
                    verify_result(x, method, result)
        print('Passed 512 binary 3x3 inputs and 12 analytical controls. CMR included:', bool(cmr))
    else:
        if args.repeats < 1 or args.time_limit <= 0 or (args.take is not None and args.take < 1):
            parser.error('repeats, time-limit and take must be positive')
        data = load_dataset(args.data)
        validate(data)
        benchmark(args, data['matrices'])


if __name__ == '__main__':
    main()
