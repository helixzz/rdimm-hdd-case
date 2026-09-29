"""Prepare local Bambu projects with public installed presets and explicit supports.

No user presets, printer connection information or print commands are used.
Full vendor presets / G-code stay in ignored build output, never committed.
"""
from pathlib import Path
import argparse
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from check_bambu_v3 import read_mesh, components

ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = {
    'layer_height': '0.2', 'initial_layer_print_height': '0.2',
    'wall_loops': '2', 'top_shell_layers': '5', 'top_shell_thickness': '1',
    'bottom_shell_layers': '3', 'bottom_shell_thickness': '0',
    'sparse_infill_density': '15%', 'sparse_infill_pattern': 'grid', 'infill_direction': '45',
    'wall_generator': 'classic', 'enable_prime_tower': '0', 'print_sequence': 'by layer',
    'enable_support': '1', 'support_type': 'normal(auto)', 'support_style': 'snug',
    'support_on_build_plate_only': '0', 'support_threshold_angle': '30',
    'support_top_z_distance': '0.2', 'support_bottom_z_distance': '0.2',
    'support_object_xy_distance': '0.35', 'support_interface_top_layers': '3',
    'support_interface_bottom_layers': '2', 'support_interface_spacing': '0.25',
    'support_filament': '0', 'support_interface_filament': '0',
    'bridge_no_support': '0', 'bridge_speed': ['50', '50', '50'],
}


def prepare(args):
    version=getattr(args,'version','3.2-rc1')
    def resolve(kind, name):
        data = json.loads((args.profiles/kind/(name+'.json')).read_text(encoding='utf8'))
        out = resolve(kind, data['inherits']) if data.get('inherits') else {}
        for inc in data.get('include', []):
            out.update(resolve(kind, inc))
        out.update(data)
        out.pop('inherits', None)
        out.pop('include', None)
        return out
    machine = resolve('machine', 'Bambu Lab P2S 0.4 nozzle')
    filament = resolve('filament', 'Bambu PLA Basic @BBL P2S')
    filament['override_process_overhang_speed'] = ['0']
    process = resolve('process', '0.20mm Standard @BBL P2S')
    process.update(OVERRIDES)
    process.update(name='RDIMM '+version+' - supports required', **{'from': 'User', 'print_settings_id': 'RDIMM '+version+' - supports required'})
    reports = []
    for label in args.plates:
        stem = 'rdimm-'+version+'-plate-'+label
        folder = (args.output_dir/label).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in [('machine', machine), ('filament', filament), ('process', process)]:
            (folder/(name+'.json')).write_text(json.dumps(data), encoding='utf8')
        project = folder/(stem+'-P2S-PLA-Basic.3mf')
        common = [str(args.bambu), '--arrange', '0', '--load-settings', str(folder/'machine.json')+';'+str(folder/'process.json'),
                  '--load-filaments', str(folder/'filament.json'), '--curr-bed-type', 'Textured PEI Plate']
        commands = [common+['--export-3mf', str(project), str((args.models/(stem+'.3mf')).resolve())],
                    [str(args.bambu), '--arrange', '0', '--slice', '0', '--outputdir', str(folder), str(project)]]
        for i, cmd in enumerate(commands):
            run = subprocess.run(cmd, cwd=folder, capture_output=True, timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            (folder/('step-'+str(i)+'.log')).write_bytes(run.stdout+run.stderr)
            assert run.returncode == 0, (label, i, run.returncode)
        result = json.loads((folder/'result.json').read_text())
        assert result['return_code'] == 0 and len(result['sliced_plates']) == 1
        with zipfile.ZipFile(project) as z:
            settings = json.loads(z.read('Metadata/project_settings.config'))
            assert settings['enable_support'] == '1'
            assert settings['support_on_build_plate_only'] == '0'
            for n in z.namelist():
                if n.endswith(('.config', '.model', '.json', '.xml')):
                    content = z.read(n).decode('utf8')
                    assert 'C:\\Users\\' not in content and 'C:/Users/' not in content, ('private path', n)
        before, after = read_mesh(args.models/(stem+'.3mf')), read_mesh(project)
        assert np.allclose(before.bounds, after.bounds, atol=.0002)
        assert abs(before.volume-after.volume) < .05
        assert components(before) == components(after)
        p = result['sliced_plates'][0]
        assert p['feature_type_times'].get('Support interface', 0) > 0
        reports.append({'plate': label, 'project': project.name, 'estimated_seconds': p['total_predication'],
                        'grams': p['filaments'][0]['total_used_g'], 'feature_seconds': p['feature_type_times'], 'warnings': p['warning_message']})
        print(json.dumps(reports[-1]), flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/'slicing-report.json').write_text(json.dumps({'version': version, 'overrides': OVERRIDES, 'results': reports,
                                                                'physical_tested': False, 'support_removal_verified': False}, indent=2), encoding='utf8')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bambu', type=Path, required=True)
    p.add_argument('--version', default='3.2-rc1')
    p.add_argument('--profiles', type=Path, required=True)
    p.add_argument('--models', type=Path, default=ROOT/'build/v3.2-rc1')
    p.add_argument('--output-dir', type=Path, default=ROOT/'build/v3.2-rc1-projects')
    p.add_argument('--plates', nargs='+', default=['1-pin-clearance', '1-body-only', '2-all-trays', '0-checks'])
    prepare(p.parse_args())
