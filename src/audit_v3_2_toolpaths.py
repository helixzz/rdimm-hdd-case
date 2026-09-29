"""Finite-width checks of Bambu paths at named v3.2 RC1 risk regions.

Nominal swept bead footprints, not material/thermal/strength simulation.
G-code and vendor profiles remain local; publish only derived audit data.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import numpy as np
from check_v3_2_supports import regions
import build_v3 as v3
import build_simple_trays as simple

ROOT = Path(__file__).resolve().parents[1]
STEP = .025


def parse(path):
    x = y = z = e = 0.
    relative_xyz, relative_e = False, True
    feature, width, height = 'Custom', None, None
    out = []
    for line in path.read_text(encoding='utf8').splitlines():
        if line.startswith('; FEATURE: '): feature = line.split(': ', 1)[1]
        if line.startswith('; LINE_WIDTH: '): width = float(line.split(': ', 1)[1])
        if line.startswith('; LAYER_HEIGHT: '): height = float(line.split(': ', 1)[1])
        code = line.split(';', 1)[0].strip()
        if not code: continue
        op = code.split()[0]
        d = {k: float(v) for k, v in re.findall(r'([XYZEFIJ])(-?(?:\d+(?:\.\d*)?|\.\d+))', code)}
        if op == 'G90': relative_xyz = False
        if op == 'G91': relative_xyz = True
        if op == 'M82': relative_e = False
        if op == 'M83': relative_e = True
        if op == 'G92':
            x, y, z, e = (d.get(k, old) for k, old in zip('XYZE', [x, y, z, e]))
        if op not in ['G0', 'G1', 'G2', 'G3']: continue
        nx, ny, nz = (old+d.get(k, 0.) if relative_xyz else d.get(k, old) for k, old in zip('XYZ', [x, y, z]))
        de = d.get('E', 0.) if relative_e else d.get('E', e)-e
        e = e+de
        if de > 0 and feature != 'Custom' and (math.hypot(nx-x, ny-y) > .00001 or op in ['G2', 'G3']):
            assert width and height, ('Missing bead metadata', line)
            assert abs(nz-z) < .002, ('Nonplanar deposition unsupported', line)
            points = [(x, y), (nx, ny)]
            if op in ['G2', 'G3']:
                assert 'I' in d or 'J' in d, ('Unsupported arc', line)
                cx, cy = x+d.get('I', 0), y+d.get('J', 0)
                a, b = math.atan2(y-cy, x-cx), math.atan2(ny-cy, nx-cx)
                sweep = ((a-b) if op == 'G2' else (b-a)) % (2*math.pi)
                if sweep < 1e-10: sweep = 2*math.pi
                radius = math.hypot(x-cx, y-cy)
                points = [(cx+radius*math.cos(t), cy+radius*math.sin(t)) for t in np.linspace(a, a+(-sweep if op == 'G2' else sweep), max(2, math.ceil(radius*sweep/.05)+1))]
                points[0], points[-1] = (x, y), (nx, ny)
            for p, q in zip(points, points[1:]):
                out.append([*p, *q, nz, width, height, float(feature.startswith('Support'))])
        x, y, z = nx, ny, nz
    return np.array(out)


def select(segs, rect):
    x0, y0, x1, y1 = rect
    return segs[(np.minimum(segs[:, 0], segs[:, 2])-segs[:, 5]/2 < x1) &
                (np.maximum(segs[:, 0], segs[:, 2])+segs[:, 5]/2 > x0) &
                (np.minimum(segs[:, 1], segs[:, 3])-segs[:, 5]/2 < y1) &
                (np.maximum(segs[:, 1], segs[:, 3])+segs[:, 5]/2 > y0)]


def grid(rect):
    x0, y0, x1, y1 = rect
    return np.meshgrid(np.arange(x0+STEP/2, x1, STEP), np.arange(y0+STEP/2, y1, STEP))


def footprint(s, xx, yy):
    x, y, qx, qy, _, width, _, _ = s
    dx, dy = qx-x, qy-y
    t = np.clip(((xx-x)*dx+(yy-y)*dy)/max(dx*dx+dy*dy, 1e-15), 0, 1)
    return (xx-x-t*dx)**2+(yy-y-t*dy)**2 <= (width/2)**2


def transformed_rect(rect, transform):
    p = [transform @ np.array([x, y, 0., 1.]) for x, y in [(rect[0], rect[1]), (rect[2], rect[3])]]
    return [min(p[0][0], p[1][0]), min(p[0][1], p[1][1]), max(p[0][0], p[1][0]), max(p[0][1], p[1][1])]


def segment_distances(s, others):
    a, b, c, d = s[:2], s[2:4], others[:, :2], others[:, 2:4]
    def point_line(p, u, v):
        uv = v-u
        t = np.clip(np.sum((p-u)*uv, axis=-1)/np.maximum(np.sum(uv*uv, axis=-1), 1e-15), 0, 1)
        return np.linalg.norm(p-u-t[..., None]*uv, axis=-1)
    result = np.minimum.reduce([point_line(a, c, d), point_line(b, c, d), point_line(c, a, b), point_line(d, a, b)])
    def cross(u, v): return u[..., 0]*v[..., 1]-u[..., 1]*v[..., 0]
    # Strict crossing; collinear/endpoint cases already covered by distances.
    crossing = (cross(b-a, c-a)*cross(b-a, d-a) < 0) & (cross(d-c, a-c)*cross(d-c, b-c) < 0)
    result[crossing] = 0
    return result


def side_gap(segs, rect, zlo, zhi):
    near = select(segs, [rect[0]-1, rect[1]-1, rect[2]+1, rect[3]+1])
    near = near[(near[:, 4] > zlo+.001) & (near[:, 4]-near[:, 6] < zhi-.001)]
    model, supports = near[near[:, 7] == 0], near[near[:, 7] == 1]
    best = np.inf
    for s in supports:
        # Only compare beads whose deposited Z intervals overlap.
        others = model[(model[:, 4] > s[4]-s[6]+.002) & (model[:, 4]-model[:, 6] < s[4]-.002)]
        if len(others):
            gap = segment_distances(s, others)-(s[5]+others[:, 5])/2
            best = min(best, float(gap.min()))
    return round(best, 4) if math.isfinite(best) else None


def run(folder, models):
    records = json.loads((models/'verification.json').read_text())['plate_records']
    report = {'method': {'xy_sample_mm': STEP, 'arc_max_segment_mm': .05,
                         'bead': 'G-code LINE_WIDTH capsule; Z interval from actual LAYER_HEIGHT',
                         'limits': 'Nominal paths only. No flow, sag, adhesion, removal, forces or fatigue simulation.'}, 'plates': []}
    for label in ['0-checks', '1-body-only', '2-all-trays', '1-pin-clearance']:
        path = folder/label/'plate_1.gcode'
        segs = parse(path)
        record = next(r for r in records if r['stem'].endswith('plate-'+label))
        checks = []
        for roi in regions(record):
            nearby = select(segs, roi['rect'])
            roof = roi['roof_z']
            xx, yy = grid(roi['rect'])
            top = np.full(xx.shape, -np.inf)
            bottom = np.full(xx.shape, np.inf)
            for s in nearby[(nearby[:, 7] == 1) & (nearby[:, 4] >= roof-.5) & (nearby[:, 4] < roof-.05)]:
                mask = footprint(s, xx, yy)
                top[mask] = np.maximum(top[mask], s[4])
            for s in nearby[(nearby[:, 7] == 0) & (nearby[:, 4]-nearby[:, 6] >= roof-.05) & (nearby[:, 4]-nearby[:, 6] < roof+.4)]:
                mask = footprint(s, xx, yy)
                bottom[mask] = np.minimum(bottom[mask], s[4]-s[6])
            overlap = np.isfinite(top) & np.isfinite(bottom)
            assert overlap.any(), ('No support/model XY overlap', label, roi)
            gaps = bottom[overlap]-top[overlap]
            assert gaps.min() >= .19, ('Top support gap insufficient', label, roi, gaps.min())
            checks.append({**roi, 'min_nominal_top_gap_mm': round(float(gaps.min()), 4),
                           'max_nominal_top_gap_mm': round(float(gaps.max()), 4),
                           'model_footprint_mm2': round(float(np.isfinite(bottom).sum()*STEP**2), 3),
                           'support_overlap_mm2': round(float(overlap.sum()*STEP**2), 3),
                           'min_local_support_model_xy_gap_mm': side_gap(segs, roi['rect'], max(0, roof-2), roof+.6)})
        corridors = []
        for pose in record['poses']:
            name, t = pose['part'], np.array(pose['assembly_to_plate'])
            candidates = []
            if name.startswith('tray-') or name == 'test-tray-1':
                n = 1 if name == 'test-tray-1' else 2 if name == 'tray-bottom-2' else 3
                for i, sy in enumerate(v3.layout(n)[2]):
                    y = simple.clip_start(n, i, sy)
                    # Center 0.5 mm of the nominal 0.9 mm through slit;
                    # exclude the intentional root and retaining tooth.
                    candidates.append((f'beam slit {i+1}', [141.3, y+1, 141.8, y+13], 0., 6.2))
            if name.startswith('body-') or name == 'latch-test-base':
                candidates.append(('leaf free-end gap', [77.3, .1, 77.7, 1.5], 23., 26.))
            for title, rect, lo, hi in candidates:
                rect = transformed_rect(rect, t)
                nearby = select(segs, rect)
                zlo, zhi = lo+t[2, 3], hi+t[2, 3]
                nearby = nearby[(nearby[:, 4] > zlo+.01) & (nearby[:, 4]-nearby[:, 6] < zhi-.01)]
                xx, yy = grid(rect)
                hits = [s for s in nearby if footprint(s, xx, yy).any()]
                corridors.append({'part': name, 'name': title, 'rect': rect, 'z_interval': [zlo, zhi], 'intruding_segments': len(hits), 'intrusions': [s.tolist() for s in hits], 'min_local_support_model_xy_gap_mm': side_gap(segs, rect, zlo, zhi)})
        report['plates'].append({'plate': label, 'gcode_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'supports': checks, 'free_corridors': corridors})
        for c in corridors:
            assert all(s[7] == 1 for s in c['intrusions']), ('Model closes free corridor', label, c)
            if c['intrusions']:
                # Observed optional coupon exception: a short removable first-
                # layer support base enters the tooth end of the slit. No
                # production-plate intrusion or higher-layer fill is accepted.
                assert label == '0-checks' and c['part'] == 'test-tray-1'
                assert all(abs(s[4]-.2) < .001 for s in c['intrusions'])
        for r in checks+corridors:
            gap = r['min_local_support_model_xy_gap_mm']
            assert gap is None or gap > .10, ('Nominal support/model side contact', label, r)
        print(label, len(checks), 'supported undersides;', len(corridors), 'corridors;', sum(c['intruding_segments'] for c in corridors), 'intrusions to review', flush=True)
    (folder/'finite-width-audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')


def check_math():
    # Independent controls for the geometry used to evaluate swept paths.
    s = np.array([0, 0, 2, 0, .4, .4, .2, 1.])
    others = np.array([[0, .6, 2, .6, .4, .4, .2, 0],
                       [1, -1, 1, 1, .4, .4, .2, 0],
                       [3, 0, 4, 0, .4, .4, .2, 0]])
    assert np.allclose(segment_distances(s, others), [.6, 0, 1])
    assert np.isclose(side_gap(np.vstack([s, others[0]]), [0, 0, 2, 1], 0, 1), .2)
    assert np.isclose(side_gap(np.vstack([s, others[1]]), [0, 0, 2, 1], 0, 1), -.4)
    elevated = others[0].copy(); elevated[4] = .8
    assert side_gap(np.vstack([s, elevated]), [0, 0, 2, 1], 0, 1) is None
    assert footprint(s, np.array([1., 1., -.1]), np.array([.1, .3, 0])).tolist() == [True, False, True]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT/'build/v3.2-rc1-recheck')
    parser.add_argument('--models', type=Path, default=ROOT/'models/v3.2-rc1')
    args = parser.parse_args()
    check_math()
    run(args.folder, args.models)
