"""Re-slice the exact delivered projects, without overriding their settings."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    manifest = json.loads((args.delivery/'manifest.json').read_text())
    results = []
    for item in manifest['files']:
        source = (args.delivery/item['file']).resolve()
        assert source.parent == args.delivery.resolve()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == item['sha256']
        folder = (args.output_dir/item['plate']).resolve()
        assert folder.parent == args.output_dir.resolve()
        folder.mkdir(parents=True, exist_ok=True)
        cmd = [str(args.bambu), '--arrange', '0', '--slice', '0', '--outputdir', str(folder), str(source)]
        result = subprocess.run(cmd, cwd=folder, capture_output=True, timeout=90,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (folder/'cli.log').write_bytes(result.stdout+result.stderr)
        assert result.returncode == 0, (item['plate'], result.returncode)
        data = json.loads((folder/'result.json').read_text())
        assert data['return_code'] == 0 and len(data['sliced_plates']) == 1
        plate = data['sliced_plates'][0]
        assert '; EXECUTABLE_BLOCK_END' in (folder/'plate_1.gcode').read_text(encoding='utf8')
        record = {**item, 'seconds': plate['total_predication'], 'grams': plate['filaments'][0]['total_used_g'], 'warnings': plate['warning_message']}
        with zipfile.ZipFile(source) as z:
            config = json.loads(z.read('Metadata/project_settings.config'))
            record['settings'] = {k: config[k] for k in ['enable_support', 'support_type', 'support_style', 'support_on_build_plate_only', 'support_top_z_distance', 'support_bottom_z_distance', 'support_object_xy_distance', 'layer_height', 'wall_generator']}
        results.append(record)
        print(item['plate'], 'sliced', record['seconds'], flush=True)
    (args.output_dir/'fresh-slices.json').write_text(json.dumps(results, indent=2), encoding='utf8')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bambu', type=Path, required=True)
    p.add_argument('--delivery', type=Path, default=ROOT/'build/v3.2-rc1-delivery')
    p.add_argument('--output-dir', type=Path, default=ROOT/'build/v3.2-rc1-recheck')
    run(p.parse_args())
