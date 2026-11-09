"""Analyse saved E2 measurements; never calls a recogniser.

python3 analyse.py results/main_run [--plots]
Tables use the standard library. --plots additionally requires Matplotlib.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import statistics as stats

from e2 import DEFAULT_DATA, load_dataset
from summarise import summarise

METHODS = ['brute', 'gh', 'cmr']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def cell(record):
    """Return condition and controlled x variable; rectangular graph rows vary."""
    p, family = record['parameters'], record['family']
    if family == 'bipartite':
        return f"p={p['p']}", p['vertices']
    if family == 'interval':
        return p['length_class'], p['order']
    if family == 'block_cycles':
        return f"blocks={p['blocks']}", p['order']
    return 'default', record['columns']


def analyse(directory, data_path, plots, output=None):
    output = output or Path(__file__).resolve().parent / "analysis"
    if output.resolve() == directory.resolve():
        raise ValueError("Analysis output must be separate from benchmark results")
    metadata = json.loads((directory / 'metadata.json').read_text())
    if not metadata.get('finished_utc'):
        raise ValueError('Analysis requires a finished run')
    if sha(directory / 'results.csv') != metadata['results_sha256']:
        raise ValueError('Raw results do not match the recorded hash')
    dataset = load_dataset(data_path)
    # Also check against the benchmark's manifest, not just its current hashes.
    base = data_path if data_path.is_dir() else data_path.parent
    for name, expected in metadata['input_sha256'].items():
        if sha(base / name) != expected:
            raise ValueError(f'Input differs from the measured dataset: {name}')
    records = {r['id']: r for r in dataset['matrices']}
    with (directory / 'results.csv').open() as handle:
        raw = list(csv.DictReader(handle))
    repeats = metadata['arguments']['repeats']
    expected_keys = set(itertools.product(metadata['selected_ids'], metadata['arguments']['methods'], range(1, repeats + 1)))
    actual_keys = [(r['instance_id'], r['method'], int(r['repetition'])) for r in raw]
    if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != expected_keys:
        raise ValueError('Missing, unexpected or duplicate repetitions')
    for r in raw:
        if r['status'] not in ['ok', 'timeout']:
            raise ValueError('Resolve failed measurements before analysing')
        if r['status'] == 'ok' and r['decision'] != str(records[r['instance_id']]['expected_tu']):
            raise ValueError('Incorrect recognition decision')
    output.mkdir(parents=True, exist_ok=True)
    previous_metadata = output / 'analysis_metadata.json'
    previous = json.loads(previous_metadata.read_text()) if previous_metadata.exists() else {}
    reuse_figures = (not plots and previous.get('raw_sha256') == sha(directory / 'results.csv')
                    and previous.get('source_sha256') == sha(Path(__file__))
                    and previous.get('plotted', False)
                    and all((output / 'figures' / f'{name}.{ext}').exists()
                            for name in ['scaling', 'properties', 'blocks'] for ext in ['png', 'pdf']))
    summarise(directory, output / "analysis.md")
    with (directory / 'summary.csv').open() as handle:
        summaries = list(csv.DictReader(handle))
    by_input = defaultdict(dict)
    for r in summaries:
        by_input[r['instance_id']][r['method']] = r
    cells = defaultdict(list)
    for r in summaries:
        rec = records[r['instance_id']]
        if rec['family'] in ['control', 'transformed']:
            continue
        condition, size = cell(rec)
        cells[(rec['family'], condition, size, r['method'])].append(r)
    cell_rows = []
    for (family, condition, size, method), group in sorted(cells.items()):
        finished = [r for r in group if r['median_wall_seconds']]
        times = [float(r['median_wall_seconds']) for r in finished]
        algorithm_times = [float(r['median_algorithm_seconds']) for r in group if r['median_algorithm_seconds']]
        algorithm_complete = len(algorithm_times) == len(group)
        all_complete = len(finished) == len(group)
        rr = [records[r['instance_id']] for r in group]
        cell_rows.append(dict(family=family, condition=condition, size=size, method=method,
            inputs=len(group), fully_completed=len(finished),
            completed_invocations=sum(int(r['completed']) for r in group),
            attempts=len(group)*repeats, rows_min=min(x['rows'] for x in rr),
            rows_max=max(x['rows'] for x in rr), columns=rr[0]['columns'],
            nonzeros_min=min(x['nonzeros'] for x in rr), nonzeros_max=max(x['nonzeros'] for x in rr),
            median_algorithm_ms=1000*stats.median(algorithm_times) if algorithm_complete else '',
            min_algorithm_ms=1000*min(algorithm_times) if algorithm_complete else '',
            max_algorithm_ms=1000*max(algorithm_times) if algorithm_complete else '',
            median_wall_ms=1000*stats.median(times) if all_complete else '',
            min_instance_median_ms=1000*min(times) if all_complete else '',
            max_instance_median_ms=1000*max(times) if all_complete else ''))
    if not cell_rows:
        raise ValueError('No scaling families selected; use summarise.py for a control-only run')
    write_csv(output / 'scaling.csv', cell_rows)

    paired = []
    for a, b in itertools.combinations(METHODS, 2):
        timing_scope = 'algorithm' if (a, b) == ('brute', 'gh') else 'wall'
        for family in ['all', 'main_only'] + sorted({r['family'] for r in records.values()}):
            eligible = []
            total = 0
            for instance, methods in by_input.items():
                rec = records[instance]
                if family == 'main_only' and rec['group'] != 'main':
                    continue
                if family not in ['all', 'main_only'] and rec['family'] != family:
                    continue
                if a not in methods or b not in methods:
                    continue
                total += 1
                x, y = methods[a][f'median_{timing_scope}_seconds'], methods[b][f'median_{timing_scope}_seconds']
                if x and y:
                    eligible.append((float(x), float(y)))
            if not total:
                continue
            ratios = [x/y for x, y in eligible]
            paired.append(dict(family=family, method_a=a, method_b=b, timing_scope=timing_scope, shared_inputs=total,
                both_fully_completed=len(eligible), excluded_incomplete=total-len(eligible),
                a_faster=sum(x < y for x, y in eligible), b_faster=sum(y < x for x, y in eligible),
                ties=sum(x == y for x, y in eligible),
                median_a_over_b=stats.median(ratios) if ratios else ''))
    write_csv(output / 'paired.csv', paired)

    transformed = []
    for instance, methods in by_input.items():
        rec = records[instance]
        if rec['group'] != 'transformed':
            continue
        for method, result in methods.items():
            parent = by_input.get(rec['parent_id'], {}).get(method)
            if parent is None:
                continue
            x, y = result['median_wall_seconds'], parent['median_wall_seconds']
            transformed.append(dict(instance_id=instance, parent_id=rec['parent_id'],
                transformation=rec['transformation'], method=method,
                variant_completed=result['completed'], parent_completed=parent['completed'],
                repetitions=repeats, variant_over_parent=float(x)/float(y) if x and y else ''))
    if transformed:
        write_csv(output / 'transformed_pairs.csv', transformed)

    results_link = Path(os.path.relpath(directory, output)).as_posix()
    lines = ['# E2 scaling and structure analysis', '',
        f'Source run: [measurements]({results_link}/results.csv), [summary]({results_link}/summary.csv) and [metadata]({results_link}/metadata.json).', '',
        'Generated from saved measurements by `analyse.py`; no recognition was rerun.', '',
        '## How to read the results', '',
        f"Each input has {repeats} repetitions with a {metadata['arguments']['time_limit']:g}-second wall limit per invocation.",
        'Each input first contributes its median across repetitions. A cell median then gives equal weight to its inputs.',
        'Cell timings and ranges appear only if every input finished every repetition; otherwise the timing is **censored**.',
        'The range is the minimum–maximum of input medians, not a confidence interval. Ten random draws are not thirty independent instances.',
        'No timeout duration is substituted for an actual recognition time. Individual completed points may still appear in plots.', '',
        '## Paired method comparisons', '',
        'Comparisons use the same inputs, with every repetition complete for both methods. Brute/GH uses algorithm time, excluding worker startup and input/output; comparisons with CMR use end-to-end wall time. Ratios are A/B; above 1 favours B.',
        'Incomplete pairs are excluded explicitly; their unobserved speed ratios cannot be inferred.', '',
        '| Inputs | A | B | Timing | Eligible / shared | A faster | B faster | Median A/B |',
        '|---|---|---|---|---:|---:|---:|---:|']
    for r in paired:
        if r['family'] in ['all', 'main_only']:
            ratio = f"{r['median_a_over_b']:.3f}" if r['median_a_over_b'] != '' else '—'
            lines.append(f"| {r['family']} | {r['method_a']} | {r['method_b']} | {r['timing_scope']} | {r['both_fully_completed']}/{r['shared_inputs']} | {r['a_faster']} | {r['b_faster']} | {ratio} |")
    lines += ['', 'Controls and transformed copies are included in `all`; `main_only` excludes transformed copies but retains controls.',
        'The full family breakdown is in [paired.csv](paired.csv). Small timing differences are descriptive, not significance tests.', '',
        '## Findings from the property comparisons', '']
    def measured(family, condition, size, method):
        return next((r for r in cell_rows if (r['family'], r['condition'], r['size'], r['method']) ==
                     (family, condition, size, method)), None)
    sparse = measured('bipartite', 'p=0.2', 12, 'gh')
    dense = measured('bipartite', 'p=0.6', 12, 'gh')
    if sparse and dense and sparse['median_wall_ms'] != '' and dense['median_wall_ms'] != '':
        lines += [f"- At 12 graph vertices, GH's cell median was {sparse['median_wall_ms']:.1f} ms at p=0.2 "
                  f"and {dense['median_wall_ms']:.1f} ms at p=0.6. Denser graphs also have more constraint rows, "
                  'so this combines a size and density effect. These are separate random samples, not matched graph pairs.']
    short = measured('interval', 'short', 10, 'brute')
    long = measured('interval', 'long', 10, 'brute')
    if short and long and short['median_wall_ms'] != '' and long['median_wall_ms'] != '':
        lines += [f"- For 10x10 interval matrices, brute-force cell medians were {short['median_wall_ms']:.1f} ms "
                  f"(short intervals) and {long['median_wall_ms']:.1f} ms (long intervals). "
                  'Both settings check all minors, but the entries affect determinant work. The effect is not universal: '
                  'GH has no consistent increasing runtime pattern across the two interval settings.']
    for count in [2, 4]:
        pairs = []
        for r in cell_rows:
            if (r['family'], r['condition'], r['method']) != ('block_cycles', f'blocks={count}', 'cmr'):
                continue
            base_row = measured('block_cycles', 'blocks=1', r['size'], 'cmr')
            if base_row and r['median_wall_ms'] != '' and base_row['median_wall_ms'] != '':
                pairs.append(r['median_wall_ms'] < base_row['median_wall_ms'])
        if pairs:
            lines += [f'- With dimensions and nonzero count fixed, CMR was faster with {count} blocks than '
                      f'one block at {sum(pairs)}/{len(pairs)} tested orders. The mixed direction gives no '
                      'consistent end-to-end benefit from adding blocks; these millisecond differences may reflect startup noise.']
    lines += ['',
        '## Runtime versus size and input properties', '',
        'Bipartite size is graph vertex count; actual matrix rows vary with edge probability. Other size values are square matrix orders.',
        'Changing p therefore changes both edge density and row count; it does not isolate density at fixed matrix dimensions.',
        'Interval settings hold dimensions fixed but change interval lengths and nonzero count.',
        'Block-cycle settings hold total dimensions and nonzero count fixed, varying the number of equal cycle blocks.', '']
    for family in ['even_cycle', 'odd_cycle', 'embedded_triangle', 'bipartite', 'interval', 'block_cycles']:
        subset = [r for r in cell_rows if r['family'] == family]
        if not subset:
            continue
        lines += [f'### {family}', '',
            'Each entry is **completed inputs / inputs; median milliseconds [range]**. Censored means at least one input did not finish all repetitions.', '',
            '| Setting | Size | Brute | GH | CMR |', '|---|---:|---|---|---|']
        for condition, size in sorted({(r['condition'], r['size']) for r in subset}):
            values = []
            for method in METHODS:
                r = next((r for r in subset if (r['condition'], r['size'], r['method']) == (condition, size, method)), None)
                if r is None:
                    values.append('—')
                    continue
                value = f"{r['fully_completed']}/{r['inputs']}; "
                if r['median_wall_ms'] == '':
                    value += 'censored'
                else:
                    value += f"{r['median_wall_ms']:.3f} [{r['min_instance_median_ms']:.3f}, {r['max_instance_median_ms']:.3f}]"
                values.append(value)
            lines.append(f"| {condition} | {size} | " + ' | '.join(values) + ' |')
        lines.append('')
    if transformed:
        lines += ['## Paired representation checks', '',
            'All completed variants agree with their construction labels. A timed-out variant does not establish a decision.',
            'Counts below are variant–parent pairs; a parent may appear in several pairs. They are not independent samples.', '',
            '| Method | Pairs | Both fully completed | Different completion counts | Median variant / parent |',
            '|---|---:|---:|---:|---:|']
        for method in METHODS:
            group = [r for r in transformed if r['method'] == method]
            ratios = [r['variant_over_parent'] for r in group if r['variant_over_parent'] != '']
            ratio = f'{stats.median(ratios):.3f}' if ratios else '—'
            lines.append(f"| {method} | {len(group)} | {len(ratios)} | {sum(r['variant_completed'] != r['parent_completed'] for r in group)} | {ratio} |")
        lines += ['', 'Individual transformations and paired ratios are in [transformed_pairs.csv](transformed_pairs.csv).', '']
    if plots:
        make_plots(output, cell_rows, summaries, records, metadata['arguments']['time_limit'])
    if plots or reuse_figures:
        lines += ['## Figures', '',
            'Circles show fully completed input medians. Lines join cell medians only when the whole cell completed.',
            'Top panels use wall time for all methods; bottom panels use algorithm time for brute and GH only. CMR has no comparable saved algorithm time.',
            'Whiskers show the range of input medians. Triangles mark wall-clock timeouts; their vertical position is not a measured algorithm time or an algorithm-time lower bound.',
            'Colours identify methods. Horizontal offsets separate overlapping methods and are only visual.', '',
            '![Cycle and obstruction scaling](figures/scaling.png)', '',
            '![Bipartite density and interval length](figures/properties.png)', '',
            '![Fixed-size block comparison](figures/blocks.png)', '',
            'Matching vector PDF files are available alongside each PNG for report export.', '']
    lines += ['## Interpretation limits', '',
        'Property tables and representation checks use end-to-end wall time. Brute/GH paired comparisons and the algorithm-time figure panels exclude Python startup and input/output.',
        'Python-only algorithm timings must not be compared directly against CMR wall time. They do not resolve a tiny-input kernel crossover.',
        'The run establishes empirical behaviour on these synthetic inputs, not polynomial/exponential bounds.',
        'CMR may recognise these families by fast paths; a benefit from block structure alone does not identify which internal decomposition it used.', '']
    (output / 'analysis.md').write_text('\n'.join(lines))
    provenance = dict(generated_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
        source_sha256=sha(Path(__file__)), summarise_sha256=sha(Path(__file__).with_name('summarise.py')),
        raw_sha256=sha(directory / 'results.csv'), results_directory=results_link, plotted=plots or reuse_figures)
    if plots:
        import matplotlib
        provenance['matplotlib'] = matplotlib.__version__
    elif reuse_figures:
        provenance['matplotlib'] = previous.get('matplotlib')
        provenance['figures_reused_from'] = previous['generated_utc']
    (output / 'analysis_metadata.json').write_text(json.dumps(provenance, indent=2)+'\n')
    return len(raw), len(cell_rows), len(paired)


def make_plots(directory, cells, summaries, records, limit):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import numpy as np
    colours = dict(brute='#c44e52', gh='#dd9c26', cmr='#2878b5')
    figures = directory / 'figures'
    figures.mkdir(exist_ok=True)

    def panel(ax, family, condition, title, scope='wall'):
        plotted_methods = METHODS if scope == 'wall' else METHODS[:2]
        median_key = f'median_{scope}_ms'
        low_key = 'min_instance_median_ms' if scope == 'wall' else 'min_algorithm_ms'
        high_key = 'max_instance_median_ms' if scope == 'wall' else 'max_algorithm_ms'
        for index, method in enumerate(plotted_methods):
            factor = 1 + (index - 1)*0.025
            selected = sorted([r for r in cells if (r['family'], r['condition'], r['method']) ==
                               (family, condition, method)], key=lambda r:r['size'])
            xs, ys = [], []
            for r in selected:
                x = r['size']*factor
                xs.append(x)
                ys.append(r[median_key] if r[median_key] != '' else np.nan)
                if r[median_key] != '':
                    ax.vlines(x, r[low_key], r[high_key], color=colours[method], alpha=.6)
            ax.plot(xs, ys, color=colours[method], linewidth=1.2)
            for r in summaries:
                rec = records[r['instance_id']]
                if rec['family'] != family or r['method'] != method or cell(rec)[0] != condition:
                    continue
                x = cell(rec)[1]*factor
                if r[f'median_{scope}_seconds']:
                    ax.scatter(x, float(r[f'median_{scope}_seconds'])*1000, s=15, color=colours[method], alpha=.55)
                elif int(r['timeouts']):
                    ax.scatter(x, limit*1000, marker='^', s=35, color=colours[method], alpha=.7)
        if scope == 'wall':
            ax.axhline(limit*1000, linestyle=':', color='0.4', linewidth=.8)
        ax.set_xscale('log', base=2)
        ax.set_yscale('log')
        ticks = sorted({r['size'] for r in cells if (r['family'], r['condition']) == (family, condition)})
        ax.set_xticks(ticks, labels=[str(x) for x in ticks], rotation=30 if len(ticks) > 7 else 0)
        ax.tick_params(axis='x', labelsize=9)
        if scope == 'wall':
            ax.set_ylim(2, limit*1500)
        ax.set_title(title)
        ax.set_xlabel('Graph vertices' if family == 'bipartite' else 'Matrix order')
        ax.set_ylabel('End-to-end wall time (ms)' if scope == 'wall' else 'Python algorithm time (ms)')
        ax.grid(alpha=.15, which='both')

    groups = [
        ('scaling', (1,3), [('even_cycle','default','Even cycles (TU)'),
                            ('odd_cycle','default','Odd cycles (non-TU)'),
                            ('embedded_triangle','default','Embedded triangle (non-TU)')]),
        ('properties', (2,2), [('bipartite','p=0.2','Bipartite, p=0.2 (TU)'),
                               ('bipartite','p=0.6','Bipartite, p=0.6 (TU)'),
                               ('interval','short','Short column intervals (TU)'),
                               ('interval','long','Long column intervals (TU)')]),
        ('blocks', (1,3), [('block_cycles',f'blocks={count}',f'{count} cycle block(s) (TU)') for count in [1,2,4]])]
    for name, shape, specs in groups:
        fig, axes = plt.subplots(2*shape[0], shape[1], figsize=(5*shape[1], 7.6*shape[0]), squeeze=False)
        for scope, panel_axes in [('wall', axes[:shape[0]]), ('algorithm', axes[shape[0]:])]:
            for ax, spec in zip(panel_axes.flat, specs):
                panel(ax, *spec, scope=scope)
        handles = [Line2D([0],[0],color=colours[m],marker='o',label=m) for m in METHODS]
        handles.append(Line2D([0],[0],color='0.4',marker='^',linestyle='none',label='Wall timeout (position is not algorithm time)'))
        fig.legend(handles=handles, loc='lower center', ncol=4)
        fig.tight_layout(rect=(0,.10,1,1))
        for extension in ['png','pdf']:
            fig.savefig(figures / f'{name}.{extension}', dpi=180)
        plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--plots', action='store_true')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'analysis')
    args = parser.parse_args()
    print(analyse(args.directory, args.data, args.plots, args.output))
