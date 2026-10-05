"""Reference slicing estimates using installed Bambu profiles; never send prints.

Full vendor presets and generated G-code stay in the caller's scratch directory.
Published reports contain identifiers, hashes, comparison settings and estimates.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLATES = {'1': 'rdimm-v3.1-plate-1-pin-clearance', '2': 'rdimm-v3.1-plate-2-all-trays',
          'A': 'rdimm-v3.1-batch-a-body-lid-bottom', 'B': 'rdimm-v3.1-batch-b-middle-top-2sets'}


def benchmark(args):
    source_hashes = {}
    def resolve(kind, name):
        p = args.profiles/kind/(name+'.json')
        source_hashes[p.relative_to(args.profiles).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
        d = json.loads(p.read_text(encoding='utf-8'))
        r = resolve(kind, d['inherits']) if d.get('inherits') else {}
        for inc in d.get('include', []):
            r.update(resolve(kind, inc))
        r.update(d)
        r.pop('inherits', None)
        r.pop('include', None)
        return r
    machine = resolve('machine', 'Bambu Lab P2S 0.4 nozzle')
    filament = resolve('filament', 'Bambu PLA Basic @BBL P2S')
    base = resolve('process', '0.20mm Standard @BBL P2S')
    changes = dict(layer_height='0.2', initial_layer_print_height='0.2', wall_loops='3',
                   top_shell_layers='3', bottom_shell_layers='3', top_shell_thickness='0.6', bottom_shell_thickness='0.6',
                   sparse_infill_density='15%', enable_support='1', support_type='normal(auto)',
                   support_on_build_plate_only='0', support_threshold_angle='30', support_top_z_distance='0.2',
                   support_bottom_z_distance='0.2', support_object_xy_distance='0.35', enable_prime_tower='0',
                   print_sequence='by layer', wall_generator='arachne')
    modes = {'baseline': {}, 'infill-candidate': {'infill_combination': '1', 'internal_solid_infill_line_width': '0.5',
                                               'sparse_infill_line_width': '0.5'}}
    results = []
    for mode, delta in modes.items():
        for label, name in PLATES.items():
            folder = (args.output_dir/(mode+'-'+label)).resolve()
            folder.mkdir(parents=True, exist_ok=True)
            for config, data in [('machine', machine), ('filament', filament), ('process', {**base, **changes, **delta})]:
                (folder/(config+'.json')).write_text(json.dumps(data), encoding='utf-8')
            source = (args.models/(name+'.3mf')).resolve()
            cmd = [str(args.bambu.resolve()), '--arrange', '0', '--load-settings', str(folder/'machine.json')+';'+str(folder/'process.json'),
                   '--load-filaments', str(folder/'filament.json'), '--curr-bed-type', 'Textured PEI Plate', '--slice', '0',
                   '--export-slicedata', str(folder/'cache'), '--outputdir', str(folder), str(source)]
            run = subprocess.run(cmd, cwd=folder, capture_output=True, timeout=180,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            (folder/'cli.log').write_bytes(run.stdout+run.stderr)
            assert run.returncode == 0, (mode, label, run.returncode)
            result = json.loads((folder/'result.json').read_text())
            assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
            p = result['sliced_plates'][0]
            assert (folder/'plate_1.gcode').stat().st_size > 0
            rec = {'mode': mode, 'plate': label, 'source': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                   'estimated_total_seconds': p['total_predication'], 'estimated_model_seconds': p['main_predication'],
                   'filament_grams': p['filaments'][0]['total_used_g'], 'warnings': p['warning_message'],
                   'feature_seconds': p['feature_type_times']}
            results.append(rec)
            print(f'{mode} / {label}: {p["total_predication"]/60:.1f} min', flush=True)
    totals = {}
    for mode in modes:
        t = {r['plate']: r['estimated_total_seconds'] for r in results if r['mode'] == mode}
        totals[mode] = {'single_set_seconds': t['1']+t['2'], '10_sets_individual_seconds': 10*(t['1']+t['2']),
                        '10_sets_batch_seconds': 10*t['A']+5*t['B']}
    report = {'application': 'Bambu Studio', 'application_version': args.app_version,
              'printer': 'Bambu Lab P2S 0.4 nozzle', 'filament': 'Bambu PLA Basic @BBL P2S', 'bed': 'Textured PEI Plate',
              'common_process_overrides': changes, 'candidate_overrides': modes['infill-candidate'],
              'vendor_profile_sha256': source_hashes, 'results': results, 'totals': totals,
              'time_is_slicer_estimate_not_measured': True, 'manual_plate_change_time_included': False,
              'support_paths_visually_validated': False, 'fit_or_strength_validated': False,
              'candidate_is_not_production_validated': True,
              'scope': 'same geometry; no wall count, skin thickness, layer height, outer speed or filament flow-limit reduction',
              'method_reference': 'https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bambu', type=Path, required=True)
    parser.add_argument('--profiles', type=Path, required=True, help='Installed resources/profiles/BBL directory')
    parser.add_argument('--app-version', required=True)
    parser.add_argument('--models', type=Path, default=ROOT/'models/v3.1')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/v3.1-benchmark')
    parser.add_argument('--report', type=Path, default=ROOT/'build/v3.1-benchmark/report.json')
    benchmark(parser.parse_args())
