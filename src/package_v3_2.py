"""Package local supported projects; keep vendor profiles out of Git history."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
import numpy as np
import trimesh
import manifold3d as m
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def preview(models, out):
    im = Image.new('RGB', (1300, 780), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    title, font, small = (ImageFont.load_default(size=s) for s in [27, 21, 17])
    draw.text((25, 18), 'RDIMM v3.2 RC1 | SUPPORTS REQUIRED | physical validation pending', fill='#17324b', font=title)
    panels = [('0-checks', 'Optional checks: 4 pieces, one print'), ('2-all-trays', 'All three trays: one print')]
    for i, (label, text) in enumerate(panels):
        left, top, scale = 25+i*640, 115, 2.35
        draw.text((left, 70), text, fill='#17324b', font=font)
        draw.rectangle((left, top, left+256*scale, top+256*scale), fill='white', outline='#8a9eac', width=2)
        mesh = trimesh.load_mesh(models/('rdimm-3.2-rc1-plate-'+label+'.stl'))
        solid = m.Manifold(m.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))
        for j, s in enumerate(solid.decompose()):
            polys = m.CrossSection(s.project().to_polygons(), m.FillRule.Positive).to_polygons()
            for poly in sorted(polys, key=lambda p: -abs(np.sum(p[:, 0]*np.roll(p[:, 1], -1)-p[:, 1]*np.roll(p[:, 0], -1)))):
                area = np.sum(poly[:, 0]*np.roll(poly[:, 1], -1)-poly[:, 1]*np.roll(poly[:, 0], -1))
                draw.polygon([(left+x*scale, top+(256-y)*scale) for x, y in poly],
                             fill=['#8fb8d1', '#a7c7aa', '#e6be7d', '#bda7cd'][j%4] if area > 0 else 'white', outline='#486477')
    draw.text((25, 741), 'Open the P2S-PLA-Basic 3MF as a project, keep support settings, then slice. Do not import geometry alone.', fill='#334c61', font=small)
    im.save(out/'plate-guide.png')


def package(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for label in ['0-checks', '1-body-only', '2-all-trays', '1-pin-clearance']:
        name = 'rdimm-3.2-rc1-plate-'+label+'-P2S-PLA-Basic.3mf'
        source = args.projects/label/name
        with zipfile.ZipFile(source) as z:
            assert z.testzip() is None
            settings = json.loads(z.read('Metadata/project_settings.config'))
            assert settings['enable_support'] == '1' and settings['support_on_build_plate_only'] == '0'
        target = args.output_dir/name
        shutil.copy2(source, target)
        records.append({'file': name, 'plate': label, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    shutil.copy2(ROOT/'docs/v3.2-rc1.zh-CN.md', args.output_dir/'README.zh-CN.md')
    for name in ['slicing-report.json', 'support-audit.json']:
        shutil.copy2(args.projects/name, args.output_dir/name)
    shutil.copy2(args.models/'verification.json', args.output_dir/'geometry-checks.json')
    preview(args.models, args.output_dir)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = {'version': '3.2-rc1', 'source_commit': commit, 'physical_tested': False,
                'files': records, 'printer': 'Bambu Lab P2S 0.4 nozzle', 'material_profile': 'Bambu PLA Basic @BBL P2S',
                'bambu_studio_version': '02.08.02.61', 'complete_set_plate_count': 2,
                'optional_checks_are_not_production_parts': True, 'existing_v3_1_lid_geometry_compatible': True,
                'requires_project_open_and_reslice': True, 'gcode_included': False}
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    files = sorted(p for p in args.output_dir.iterdir() if p.is_file() and p.suffix != '.zip' and p.name != 'SHA256SUMS.txt')
    (args.output_dir/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files), encoding='utf8')
    archive = args.output_dir/'rdimm-v3.2-rc1-P2S-supported-projects.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(args.output_dir.iterdir()):
            if p.is_file() and p.suffix != '.zip':
                z.write(p, p.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(archive)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--models', type=Path, default=ROOT/'models/v3.2-rc1')
    p.add_argument('--projects', type=Path, default=ROOT/'build/v3.2-rc1-projects')
    p.add_argument('--output-dir', type=Path, default=ROOT/'build/v3.2-rc1-delivery')
    package(p.parse_args())
