"""v3.2 printability revision. Requires the accompanying support process.

Preserves the v3.1 assembly, module stops and sliding-cover operation.
Geometry checks are not force, fatigue or physical print validation.
"""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import manifold3d as m
import build_v3 as v3
import build_simple_trays as simple
from build_v3_1 import export_3mf as export_geometry

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.2-rc1'
SHELF, ROOF = 3.0, 4.6


def tilt(s, x, angle):
    return s.translate((-x, 0, -SHELF)).rotate((0, -angle, 0)).translate((x, 0, SHELF))


def old_part(name):
    records = json.loads((ROOT/'models/v3/verification.json').read_text())['parts']
    record = next(r for r in records if r['part'] == name)
    mesh = trimesh.load_mesh(ROOT/'models/v3.1'/(name+'.stl'))
    mesh.apply_translation(-np.asarray(record['translation_for_print']))
    if record['flip_x_180']:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    mesh.vertices = np.round(mesh.vertices, 4)
    return m.Manifold(m.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))


def leaf():
    # Full wall-width leaf replaces the narrow leaf plus close parallel guard.
    # The swept release stays inside the open pocket. Local slicer support is
    # compulsory below this horizontal leaf; width alone does not fix overhangs.
    return v3.box((29., 1.6, 1.), (47., 0., 23.))+v3.box((5., 1.6, 3.), (72., 0., 23.))


def revised_body(name):
    fixed = old_part(name)-v3.box((31., 1.8, 7.), (47., 0., 20.))
    return fixed+leaf(), fixed


def wedge(points, y, length):
    return m.CrossSection([points]).extrude(length).rotate((90, 0, 0)).translate((0, y+length, 0))


def revised_tray(name, n, bottom, tier):
    full, fixed, leaves = simple.simple_tray(ROOT/'models/v2-retention', name, n, bottom, tier)
    # Increase roof clearance by 0.1; preserve the PCB shelf height because
    # the bottom tray's PCB must remain above the shell connector roof.
    # Keep 0.3 below / 0.1 above the worst reference component envelope.
    for sy in v3.layout(n)[2]:
        fixed -= v3.box((1.6001, 8., .1101), (6.3, sy+12., 4.49))
    new_leaves = []
    for y, s in leaves:
        s -= v3.box((2.61, 4., .1101), (139.39, y+14., 4.49))
        cut = wedge([(139.39, 4.59), (139.81, 4.59), (139.39, 4.92)], y+14., 4.)
        new_leaves.append((y, s-cut))
    for sy in v3.layout(n)[2]:
        cut = wedge([(7.49, 4.59), (7.91, 4.59), (7.91, 4.92)], sy+12., 8.)
        fixed -= cut
    full = fixed
    for _, s in new_leaves:
        full += s
    return full, fixed, new_leaves


def write_3mf(path, mesh):
    export_geometry(path, mesh)
    with zipfile.ZipFile(path) as z:
        data = {n: z.read(n) for n in z.namelist()}
    data['3D/3dmodel.model'] = data['3D/3dmodel.model'].replace(b'RDIMM HDD case v3.1', b'RDIMM HDD case v3.2-rc1')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, value in data.items():
            z.writestr(n, value)


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    parts, fixed, leaves = {}, {}, {}
    for name in ['body-pin-clearance', 'body-thread-pilot']:
        parts[name], fixed[name] = revised_body(name)
    parts['lid-slide'] = old_part('lid-slide')
    configs = [('tray-bottom-2', 2, True, '1'), ('tray-middle-3', 3, False, '2'), ('tray-top-3', 3, False, '3')]
    for name, n, bottom, tier in configs:
        parts[name], fixed[name], leaves[name] = revised_tray(name, n, bottom, tier)
    checks = {'module_poses': 0, 'release_poses': 0, 'pcb_stops': 0}
    assembly = [parts['body-pin-clearance'], parts['lid-slide']]
    for i, (name, _, _, _) in enumerate(configs):
        assembly.append(parts[name].translate((0, 0, v3.BASE+i*v3.PITCH)))
    for i, a in enumerate(assembly):
        for b in assembly[:i]:
            assert (a^b).volume() < .0001, ('assembly collision', i)
    for a in assembly[1:]:
        assert (a^parts['body-thread-pilot']).volume() < .0001
    # Guard is deliberately removed. Check wider leaf's entire release sweep.
    for travel in np.linspace(0., 2.5, 26):
        moved = leaf().warp(lambda p: (p[0], p[1], p[2]-float(travel)*max(0., min(1., (p[0]-47.)/30.))**2))
        assert (moved^fixed['body-pin-clearance']).volume() < .0001
        for a in assembly[2:]:
            assert (moved^a).volume() < .0001
    released_body = fixed['body-pin-clearance']+moved
    assert (parts['lid-slide'].translate((0, -1., 0))^parts['body-pin-clearance']).volume() > .01
    assert (parts['lid-slide'].translate((0, 1., 0))^parts['body-pin-clearance']).volume() > .01
    assert (parts['lid-slide'].translate((0, 0, .4))^parts['body-pin-clearance']).volume() > .01
    for step in range(102):
        for a in [released_body]+assembly[2:]:
            assert (parts['lid-slide'].translate((0, -step, 0))^a).volume() < .0001, ('lid slide', step)
    for ti, (name, n, _, _) in enumerate(configs):
        for sy in v3.layout(n)[2]:
            for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
                for x, y, z in product((6.5, 140.5-length), (sy+.1, sy+31.7-width), (SHELF, ROOF-pcb)):
                    ram = simple.module(length, width, pcb, x, y, z).translate((0, 0, v3.BASE+ti*v3.PITCH))
                    for a in assembly:
                        assert (ram^a).volume() < .0001, ('module collision', name, x, y, z)
                    checks['module_poses'] += 1
            for pos in ((6.45, sy+.2, SHELF), (6.75, sy+.2, SHELF), (6.6, sy+.05, SHELF),
                        (6.6, sy+.35, SHELF), (6.6, sy+.2, SHELF-.05), (6.6, sy+.2, ROOF-1.37+.05)):
                assert (v3.box((133.8, 31.4, 1.37), pos)^parts[name]).volume() > .0001
                checks['pcb_stops'] += 1
        for i, (y, s) in enumerate(leaves[name]):
            for travel in np.linspace(0, 1.5, 16):
                moved = simple.bend(s, y, float(travel))
                assert (moved^fixed[name]).volume() < .0001
                for j, (_, other) in enumerate(leaves[name]):
                    if i != j:
                        assert (moved^other).volume() < .0001
            released = fixed[name]+simple.bend(s, y)
            for j, (_, other) in enumerate(leaves[name]):
                if i != j:
                    released += other
            sy = v3.layout(n)[2][i]
            for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
                ram = simple.module(length, width, pcb, 6.55, sy+.2, SHELF)
                for angle in np.linspace(0, 2, 21):
                    assert (tilt(ram, 6.55, float(angle))^released).volume() < .0001
                    checks['release_poses'] += 1
                for dx in np.linspace(0, 2, 21):
                    assert (tilt(ram, 6.55, 2.).translate((float(dx), 0, 0))^released).volume() < .0001
                    checks['release_poses'] += 1
    # Mount, backplane and optional lid screw spaces remain unobstructed.
    probes = [v3.box((6., 47., 6.2), (0, 11., 0))]
    for x in v3.SIDE_X:
        probes += [v3.cyl(5., 1.8, (x, 0, 6.35), rot=(-90, 0, 0)), v3.cyl(5., 1.8, (x, v3.W, 6.35), rot=(90, 0, 0))]
    for x in v3.BOTTOM_X:
        for y in v3.BOTTOM_Y:
            probes.append(v3.cyl(5., 1.8, (x, y, 0)))
    for probe in probes:
        for a in [v3.body(True)]+assembly[1:]:
            assert (probe^a).volume() < .0001
    for x, y in v3.OPTIONAL:
        screw = v3.cyl(8., 1., (x, y, 18.))+v3.countersink(x, y, 26., 4.)
        for a in assembly[2:]:
            assert (screw^a).volume() < .0001
    assert (assembly[-1].translate((0, 0, .4))^assembly[1]).volume() > .01
    for i in (2, 3):
        assert (assembly[i].translate((0, 0, .3))^assembly[i+1]).volume() > .01
    bounds = np.array([v3.meshof(a).bounds for a in assembly])
    assert np.allclose(bounds[:, 0].min(0), [0, 0, 0])
    assert np.allclose(bounds[:, 1].max(0), [147., 101.6, 26.])
    # Optional single-plate verification set, not required to build the full set.
    # It exercises one real slot, the complete lid leaf and the bottom recess.
    parts['test-tray-1'], _, _ = revised_tray('test-tray-1', 1, False, '1')
    parts['latch-test-base'] = old_part('latch-test-base')-v3.box((31., 1.8, 7.), (47., 0., 20.))+leaf()
    parts['latch-test-slider'] = old_part('latch-test-slider')
    parts['bottom-recess-test'] = parts['tray-bottom-2']^v3.box((10., 48., 6.8), (1.9, 18.1, 0.))
    assert (parts['latch-test-slider']^parts['latch-test-base']).volume() < .0001
    assert (parts['latch-test-slider'].translate((0, -1., 0))^parts['latch-test-base']).volume() > .01
    coupon_released = parts['latch-test-base']-v3.box((31., 1.8, 7.), (47., 0., 20.))
    moved_leaf = leaf().warp(lambda p: (p[0], p[1], p[2]-2.5*max(0., min(1., (p[0]-47.)/30.))**2))
    assert (moved_leaf^coupon_released).volume() < .0001
    for step in range(24):
        assert (parts['latch-test-slider'].translate((0, -step, 0))^(coupon_released+moved_leaf)).volume() < .0001
    print_meshes, transforms = {}, {}
    for name, s in parts.items():
        assert len(s.decompose()) == 1, name
        mesh = v3.meshof(s)
        transform = np.eye(4)
        if name in ('lid-slide', 'latch-test-slider'):
            transform = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
            mesh.apply_transform(transform)
        shift = -mesh.bounds[0]
        mesh.apply_translation(shift)
        transform[:3, 3] += shift
        mesh.export(out/(name+'.stl'))
        restored = trimesh.load_mesh(out/(name+'.stl'))
        assert restored.is_watertight and restored.is_winding_consistent
        assert abs(restored.volume-s.volume()) < .03
        print_meshes[name], transforms[name] = mesh, transform
    layouts = {
        'plate-1-pin-clearance': [('body-pin-clearance', 54.5, 20., False), ('lid-slide', 56.3, 130., False)],
        'plate-1-thread-pilot': [('body-thread-pilot', 54.5, 20., False), ('lid-slide', 56.3, 130., False)],
        'plate-1-body-only': [('body-pin-clearance', 54.5, 77.2, False)],
        'plate-2-all-trays': [('tray-middle-3', 15., 25.2, False), ('tray-top-3', 15., 133., False), ('tray-bottom-2', 168.2, 56.4, True)],
        'plate-0-checks': [('test-tray-1', 45., 140., False), ('latch-test-base', 35., 65., False),
                           ('latch-test-slider', 112., 65., False), ('bottom-recess-test', 190., 65., False)],
    }
    records = []
    for label, layout in layouts.items():
        meshes, poses = [], []
        for name, x, y, turn in layout:
            mesh = print_meshes[name].copy()
            rotation = trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]) if turn else np.eye(4)
            mesh.apply_transform(rotation)
            shift = np.array([x, y, 0.])-mesh.bounds[0]
            mesh.apply_translation(shift)
            transform = rotation @ transforms[name]
            transform[:3, 3] += shift
            poses.append({'part': name, 'assembly_to_plate': transform.tolist()})
            meshes.append(mesh)
        for i, mesh in enumerate(meshes):
            assert mesh.bounds[0, :2].min() >= 10.-.001 and mesh.bounds[1, :2].max() <= 246.+.001
            for other in meshes[:i]:
                gap = np.maximum(0, np.maximum(mesh.bounds[0, :2]-other.bounds[1, :2], other.bounds[0, :2]-mesh.bounds[1, :2]))
                assert np.linalg.norm(gap) >= 8.-.001
        mesh = trimesh.util.concatenate(meshes)
        stem = 'rdimm-'+VERSION+'-'+label
        mesh.export(out/(stem+'.stl'))
        write_3mf(out/(stem+'.3mf'), mesh)
        records.append({'stem': stem, 'poses': poses, 'bounds': mesh.bounds.tolist()})
    main_parts = ['body-pin-clearance', 'lid-slide', 'tray-bottom-2', 'tray-middle-3', 'tray-top-3']
    projection_area = sum(m.CrossSection(parts[name].project().to_polygons(), m.FillRule.Positive).area() for name in main_parts)
    assert projection_area > 256**2, 'Reassess the two-plate lower bound'
    report = {'version': VERSION, 'status': 'release candidate; physical validation pending', 'capacity': 8,
              'outer_mm': [147, 101.6, 26], 'complete_set_plates': 2, 'supports_required': True,
              'projection_area_mm2': projection_area, 'one_flat_plate_impossible': True,
              'plate_count_scope': 'Fixed flat orientations, no stacking, disjoint XY projections; complete five-part set only',
              'geometry_only_3mf': True, 'physical_tested': False, 'force_fatigue_retention_verified': False,
              'checks': checks, 'plate_records': records,
              'pcb_slot_height_mm': round(ROOF-SHELF, 2), 'component_clearance_below_mm': .3,
              'component_clearance_above_next_floor_mm': .1, 'unchanged_reference_module_mm': [133.8, 31.4, 5.57],
              'source_v3_1_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'models/v3.1').glob('*.stl')}}
    (out/'verification.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps({'version': VERSION, 'checks': checks, 'plates': [r['stem'] for r in records]}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/v3.2-rc1')
    build(parser.parse_args().output_dir.resolve())
