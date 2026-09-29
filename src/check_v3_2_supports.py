"""Audit generated support paths at explicitly identified v3.2 risk regions.

Support presence is a slicing check, not proof of adhesion or removability.
"""
from pathlib import Path
import argparse
import json
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_v3 as v3
import build_simple_trays as simple

ROOT = Path(__file__).resolve().parents[1]


def parse(path):
    x = y = z = 0.
    feature = 'Custom'
    relative = False
    segments = []
    for line in path.read_text(encoding='utf8').splitlines():
        if line.startswith('; FEATURE: '):
            feature = line.split(': ', 1)[1]
        code = line.split(';')[0].strip()
        if not code:
            continue
        op = code.split()[0]
        if op == 'G90': relative = False
        if op == 'G91': relative = True
        if op not in ['G0', 'G1', 'G2', 'G3']:
            continue
        d = {k: float(v) for k, v in re.findall(r'([XYZEFI J])(-?(?:\d+(?:\.\d*)?|\.\d+))', code) if k != ' '}
        nx, ny, nz = (d.get(k, 0. if relative else old)+(old if relative else 0.) for k, old in [('X', x), ('Y', y), ('Z', z)])
        if d.get('E', 0.) > 0 and feature != 'Custom' and math.hypot(nx-x, ny-y) > .0001:
            points = [(x, y), (nx, ny)]
            if op in ['G2', 'G3'] and ('I' in d or 'J' in d):
                cx, cy = x+d.get('I', 0), y+d.get('J', 0)
                a, b = math.atan2(y-cy, x-cx), math.atan2(ny-cy, nx-cx)
                sweep = ((a-b) if op == 'G2' else (b-a)) % (2*math.pi)
                radius = math.hypot(x-cx, y-cy)
                points = [(cx+radius*math.cos(t), cy+radius*math.sin(t)) for t in np.linspace(a, a+(-sweep if op == 'G2' else sweep), max(2, math.ceil(radius*sweep/.3)))]
            for p, q in zip(points, points[1:]):
                segments.append((p[0], p[1], q[0], q[1], round(nz, 3), feature))
        x, y, z = nx, ny, nz
    return segments


def regions(record):
    out = []
    def add(label, name, rect, roof, transform):
        a = transform @ np.array([rect[0], rect[1], roof, 1.])
        b = transform @ np.array([rect[2], rect[3], roof, 1.])
        out.append({'name': label, 'part': name, 'rect': [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], 'roof_z': float(a[2])})
    for pose in record['poses']:
        name, t = pose['part'], np.array(pose['assembly_to_plate'])
        if name.startswith('body-') or name == 'latch-test-base':
            add('Shell release leaf', name, [47.5, 0., 77., 1.6], 23., t)
            if name.startswith('body-'):
                add('Shell connector recess', name, [0., 11., 6.1, 58.], 6.2, t)
        elif name.startswith('tray-') or name == 'test-tray-1':
            n = 1 if name == 'test-tray-1' else 2 if name == 'tray-bottom-2' else 3
            for i, sy in enumerate(v3.layout(n)[2]):
                y = simple.clip_start(n, i, sy)
                add(name+' tooth '+str(i+1), name, [139.4, y+14., 142., y+18.], 4.6, t)
                add(name+' hood '+str(i+1), name, [6.3, sy+12., 7.9, sy+20.], 4.6, t)
                add(name+' paddle '+str(i+1), name, [142.8, y+14., 144.3, y+18.], 5.4, t)
            if n == 2:
                add('Bottom tray recess', name, [1.9, v3.layout(2)[1], 6.5, 58.2], 3.2, t)
        elif name == 'bottom-recess-test':
            add('Bottom recess coupon', name, [1.9, v3.layout(2)[1], 6.5, 58.2], 3.2, t)
    return out


def audit(args):
    records = json.loads((args.models/'verification.json').read_text())['plate_records']
    report = []
    for label in args.plates:
        record = next(r for r in records if r['stem'].endswith('plate-'+label))
        segs = parse(args.projects/label/'plate_1.gcode')
        rois = regions(record)
        for roi in rois:
            x0, y0, x1, y1 = roi['rect']
            roof = roi['roof_z']
            found = []
            for x, y, xx, yy, z, feature in segs:
                if not feature.startswith('Support') or not roof-.45 <= z < roof-.05:
                    continue
                for t in np.linspace(0, 1, max(2, int(math.hypot(xx-x, yy-y)/.15)+1)):
                    px, py = x+t*(xx-x), y+t*(yy-y)
                    if x0 <= px <= x1 and y0 <= py <= y1:
                        found.append([float(px), float(py), z])
            roi['support_sample_count'] = len(found)
            roi['support_top_z'] = max((p[2] for p in found), default=None)
            roi['support_bounds_xy'] = [np.min(np.array(found)[:, :2], axis=0).tolist(), np.max(np.array(found)[:, :2], axis=0).tolist()] if found else None
            print(roi['name'], roi['support_sample_count'], roi['support_top_z'], flush=True)
        report.append({'plate': label, 'regions': rois})
        # Readable top-down closeups: actual support paths below the risk roof.
        cols = 3
        rows = math.ceil(len(rois)/cols)
        im = Image.new('RGB', (1320, 70+rows*245), 'white')
        draw = ImageDraw.Draw(im)
        font, small = ImageFont.load_default(size=17), ImageFont.load_default(size=14)
        draw.text((20, 12), 'v3.2 RC1: generated support paths below critical features', fill='#143049', font=font)
        draw.text((20, 38), 'Orange: support toolpaths. Blue box: underside region. Presence does not prove removability.', fill='#425568', font=small)
        for i, roi in enumerate(rois):
            left, top = 20+(i%cols)*440, 75+(i//cols)*245
            draw.text((left, top), roi['name'], fill='#143049', font=small)
            x0, y0, x1, y1 = roi['rect']
            scale = min(380/max(x1-x0+3, 1), 160/max(y1-y0+3, 1))
            def pixel(x, y): return (left+20+(x-x0+1.5)*scale, top+35+(y1+1.5-y)*scale)
            for x, y, xx, yy, z, f in segs:
                if f.startswith('Support') and roi['roof_z']-.45 <= z < roi['roof_z']-.05 and min(x, xx) >= x0-1.5 and max(x, xx) <= x1+1.5 and min(y, yy) >= y0-1.5 and max(y, yy) <= y1+1.5:
                    draw.line([pixel(x, y), pixel(xx, yy)], fill='#cf7318', width=max(1, int(.3*scale)))
            draw.rectangle([pixel(x0, y1), pixel(x1, y0)], outline='#2676b5', width=2)
            draw.text((left, top+207), 'support present' if roi['support_sample_count'] else 'MISSING SUPPORT', fill='#26734f' if roi['support_sample_count'] else 'red', font=small)
        im.save(args.projects/('support-audit-'+label+'.png'))
    (args.projects/'support-audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    assert all(r['support_sample_count'] > 0 for p in report for r in p['regions']), 'Missing support in a critical region'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--models', type=Path, default=ROOT/'build/v3.2-rc1')
    p.add_argument('--projects', type=Path, default=ROOT/'build/v3.2-rc1-projects')
    p.add_argument('--plates', nargs='+', default=['1-pin-clearance', '1-body-only', '2-all-trays', '0-checks'])
    audit(p.parse_args())
