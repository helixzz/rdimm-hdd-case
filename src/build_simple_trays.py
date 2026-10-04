"""Experimental integral-latch trays for the unchanged v3 shell, mm.

Rigid and illustrative-deflection checks only: no force/fatigue prediction.
"""
from pathlib import Path
from itertools import product
import argparse
import json
import shutil
import hashlib
import numpy as np
import trimesh
import manifold3d as m
import build_v3 as v3
from operation_marks import lettering, top_cut, stroke

ROOT = Path(__file__).resolve().parents[1]


def clip_start(n, i, sy):
    return sy+(12. if n == 3 and i == 0 else 1. if (n, i) in ((3, 2), (2, 0)) else 4.)


def flexure(y):
    # In-plane flexure: constant section, fixed at y, moves outward in +X.
    beam = v3.box((.8, 18., 6.2), (142., y, 0.))
    # The tooth's top ramp guides insertion. Its lower flat roof retains PCB.
    section = m.CrossSection([[(139.4, 4.5), (142.8, 4.5), (142.8, 6.2), (141.1, 6.2), (139.4, 4.7)]])
    tooth = section.extrude(4.).rotate((90, 0, 0)).translate((0, y+18., 0))
    paddle = v3.box((2.2, 4., .8), (142.1, y+14., 5.4))
    arrow = stroke([(141.5, y+16.), (143.9, y+16.)], .45)
    arrow += stroke([(142.9, y+15.), (143.9, y+16.), (142.9, y+17.)], .45)
    return beam+tooth+paddle-top_cut(arrow, 6.2)


def bend(s, y, travel=1.5):
    # Free-end tooth translates rigidly; beam blends from its fixed root.
    return s.warp(lambda p: (p[0]+travel*min(1., max(0., (p[1]-y)/14.))**2, p[1], p[2]))


def simple_tray(models, name, n, bottom=False, tier='1'):
    a = v3.tray(models, name, n, bottom)
    width, oy, ys = v3.layout(n)
    # Replace the separate frame's bearing surfaces with fixed tray structure.
    cap = v3.box((4.4, width, 1.3), (1.9, oy, 5.5))
    a += cap+v3.opposite(cap)
    for y in (oy, oy+width-.6):
        a += v3.box((143.2, .6, 2.5), (1.9, y, 4.3))
    # All finger releases live in open pockets. Stop before posts and dividers.
    leaves = []
    for i, sy in enumerate(ys):
        y = clip_start(n, i, sy)
        # Through-slit prints the beam from the bed, with no trapped support
        # underneath. Only the small PCB hoods/teeth may need local support.
        a -= v3.box((4.1, 19., 7.), (141.1, y, -.1))
        a -= v3.box((.6, 19., 3.), (140.6, y, 4.4))
        leaf = flexure(y)
        leaves.append((y, leaf))
        # Root remains joined to the rail at y; rest of flexure is isolated.
        a += v3.box((.8, .5, 6.2), (142., y-.5, 0.))
        # Opposite end is fixed: tuck the PCB under this short, broad hood.
        a += v3.box((6., 8., 1.3), (1.9, sy+12., 5.5))
        a += v3.box((1.7, 8., 1.2), (6.2, sy+12., 4.5))
    a -= v3.end_reliefs()
    # Large layer number and lift mark on fixed left end, never on flexures.
    mark = lettering(tier+' LIFT').rotate(90).translate((5.6, 44.))
    a -= top_cut(mark, 6.8)
    static = a
    for _, leaf in leaves:
        a += leaf
    return a.set_tolerance(.0001), static, leaves


def module(length, width, pcb, x, y, z=3.):
    return v3.box((length, width, pcb), (x, y, z))+v3.box((length-4., width, pcb+4.2), (x+2., y, z-2.1))


def tilt(s, x, angle):
    return s.translate((-x, 0, -3.)).rotate((0, -angle, 0)).translate((x, 0, 3.))


def build(models, v3models, out):
    out.mkdir(parents=True, exist_ok=True)
    originals = json.loads((v3models/'verification.json').read_text())
    records = {r['part']: r for r in originals['parts']}
    def original(name):
        mesh = trimesh.load_mesh(v3models/(name+'.stl'))
        mesh.apply_translation(-np.array(records[name]['translation_for_print']))
        if records[name]['flip_x_180']:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        mesh.vertices = np.round(mesh.vertices, 4)
        mesh.merge_vertices()
        return m.Manifold(m.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))
    parts, static, leaves = {}, {}, {}
    configs = [('tray-bottom-2', 2, True, '1'), ('tray-middle-3', 3, False, '2'),
               ('tray-top-3', 3, False, '3'), ('test-tray-1', 1, False, '1')]
    for name, n, bottom, tier in configs:
        parts[name], static[name], leaves[name] = simple_tray(models, name, n, bottom, tier)
    for name in ('body-pin-clearance', 'body-thread-pilot', 'lid-slide', 'empty-fit-gauge-pin',
                 'rail-test-base', 'rail-test-slider', 'latch-test-base', 'latch-test-slider'):
        parts[name] = original(name)
        shutil.copyfile(v3models/(name+'.stl'), out/(name+'.stl'))
    counts = {'module_poses': 0, 'pcb_stop_controls': 0, 'release_sweep_poses': 0}
    for name, n, _, _ in configs:
        for sy in v3.layout(n)[2]:
            for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
                for x, y, z in product((6.5, 140.5-length), (sy+.1, sy+31.7-width), (3., 4.5-pcb)):
                    ram = module(length, width, pcb, x, y, z)
                    assert (ram^parts[name]).volume() < .0001, (name, 'module', x, y, z)
                    counts['module_poses'] += 1
            for pos in ((6.45, sy+.2, 3.), (6.75, sy+.2, 3.), (6.6, sy+.05, 3.),
                        (6.6, sy+.35, 3.), (6.6, sy+.2, 2.95), (6.6, sy+.2, 3.18)):
                pcb = v3.box((133.8, 31.4, 1.37), pos)
                assert (pcb^parts[name]).volume() > .0001, (name, 'missing PCB stop', pos)
                counts['pcb_stop_controls'] += 1
        for i, (y, leaf) in enumerate(leaves[name]):
            for travel in np.linspace(0, 1.5, 16):
                moved = bend(leaf, y, float(travel))
                assert (moved^static[name]).volume() < .0001, (name, 'flexure hits fixed rail', travel)
                for j, (_, other) in enumerate(leaves[name]):
                    if i != j:
                        assert (moved^other).volume() < .0001
            released = static[name]+bend(leaf, y)
            for j, (_, other) in enumerate(leaves[name]):
                if i != j:
                    released += other
            sy = v3.layout(n)[2][i]
            # A shallow 2-degree tilt clears the released right tooth while
            # the left PCB end stays under its fixed hood. Then withdraw +X.
            for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
                x = 6.55
                ram = module(length, width, pcb, x, sy+.2)
                for angle in np.linspace(0, 2., 21):
                    moved = tilt(ram, x, float(angle))
                    assert (moved^released).volume() < .0001, (name, 'tilt path', i, length, pcb, angle, (moved^released).volume())
                    counts['release_sweep_poses'] += 1
                for dx in np.linspace(0, 2., 21):
                    moved = tilt(ram, x, 2.).translate((float(dx), 0, 0))
                    assert (moved^released).volume() < .0001, (name, 'withdraw path', i, dx, (moved^released).volume())
                    counts['release_sweep_poses'] += 1
    assembly = [parts['body-pin-clearance'], parts['lid-slide']]
    for i, (name, _, _, _) in enumerate(configs[:3]):
        assembly.append(parts[name].translate((0, 0, v3.BASE+i*v3.PITCH)))
    for i, a in enumerate(assembly):
        for j, b in enumerate(assembly[:i]):
            assert (a^b).volume() < .0001, ('assembly', i, j, (a^b).volume())
    for a in assembly[1:]:
        assert (a^parts['body-thread-pilot']).volume() < .0001
    probes = []
    for x in v3.SIDE_X:
        probes += [v3.cyl(5., 1.8, (x, 0, 6.35), rot=(-90, 0, 0)),
                   v3.cyl(5., 1.8, (x, v3.W, 6.35), rot=(90, 0, 0))]
    for x in v3.BOTTOM_X:
        for y in v3.BOTTOM_Y:
            probes.append(v3.cyl(5., 1.8, (x, y, 0)))
    connector = v3.box((6., 47., 6.2), (0, 11., 0))
    screws = [v3.cyl(8., 1., (x, y, 18.))+v3.countersink(x, y, 26., 4.) for x, y in v3.OPTIONAL]
    # Use the exact source body for flush cylindrical probes; the copied STL
    # has float32 rounding at hole surfaces. Unengraved body is conservative.
    for ai, a in enumerate([v3.body(True)]+assembly[1:]):
        for oi, obstacle in enumerate(probes+[connector]):
            assert (a^obstacle).volume() < .0001, ('mount or connector space occupied', ai, oi, (a^obstacle).volume())
    for a in assembly[2:]:
        for screw in screws:
            assert (a^screw).volume() < .0001
    for i, (name, n, _, _) in enumerate(configs[:3]):
        for sy in v3.layout(n)[2]:
            for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
                for x, yy, zz in product((6.5, 140.5-length), (sy+.1, sy+31.7-width), (3., 4.5-pcb)):
                    ram = module(length, width, pcb, x, yy, zz).translate((0, 0, v3.BASE+i*v3.PITCH))
                    for a in assembly:
                        assert (ram^a).volume() < .0001, 'loaded assembly collision'
    bounds = np.array([v3.meshof(a).bounds for a in assembly])
    assert np.allclose(bounds[:, 0].min(0), [0, 0, 0], atol=.0001)
    assert np.allclose(bounds[:, 1].max(0), [147., 101.6, 26.], atol=.0001)
    # Closed lid captures top tray; fixed rails carry stacking loads, not tabs.
    assert (assembly[-1].translate((0, 0, .4))^assembly[1]).volume() > .01
    for i in (2, 3):
        assert (assembly[i].translate((0, 0, .3))^assembly[i+1]).volume() > .01
    for step in range(102):
        for a in assembly[2:]:
            assert (assembly[1].translate((0, -step, 0))^a).volume() < .0001
    for name, _, _, _ in configs:
        s = parts[name]
        assert len(s.decompose()) == 1, (name, 'not single part')
        mesh = v3.meshof(s)
        mesh.apply_translation(-mesh.bounds[0])
        mesh.export(out/(name+'.stl'))
        read = trimesh.load_mesh(out/(name+'.stl'))
        assert read.is_watertight and read.is_winding_consistent
        assert abs(read.volume-s.volume()) < .03
    def place(name, x, y, turn=False):
        mesh = trimesh.load_mesh(out/(name+'.stl'))
        if turn:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]))
        mesh.apply_translation(-mesh.bounds[0]+np.array([x, y, 0.]))
        return mesh
    plates = {'first-test-all': [place('empty-fit-gauge-pin', 15., 34.2), place('test-tray-1', 15., 155.),
                               place('latch-test-base', 181., 34.2), place('latch-test-slider', 181., 67.2),
                               place('rail-test-base', 181., 104.2), place('rail-test-slider', 211., 104.2)],
              'plate-2-all-trays': [place('tray-middle-3', 15., 25.2), place('tray-top-3', 15., 133.),
                                  place('tray-bottom-2', 168.2, 56.4, True)]}
    for kind in ('pin-clearance', 'thread-pilot'):
        name = 'plate-1-body-'+kind+'-lid'
        shutil.copyfile(v3models/(name+'.stl'), out/(name+'.stl'))
    reports = []
    for name, meshes in plates.items():
        for i, mesh in enumerate(meshes):
            assert mesh.bounds[0, :2].min() >= 15.-.0001 and mesh.bounds[1, :2].max() <= 241.+.0001
            assert abs(mesh.bounds[0, 2]) < .0001
            for other in meshes[:i]:
                gap = np.maximum(0, np.maximum(mesh.bounds[0, :2]-other.bounds[1, :2], other.bounds[0, :2]-mesh.bounds[1, :2]))
                assert np.linalg.norm(gap) >= 10.-.0001, (name, 'spacing')
        packed = trimesh.util.concatenate(meshes)
        packed.export(out/(name+'.stl'))
        reports.append({'file': name+'.stl', 'pieces': len(meshes), 'bounds_mm': packed.bounds.tolist(),
                        'minimum_gap_mm': 10., 'minimum_bed_margin_mm': 15.})
    report = {'variant': 'v3-simple-integral-latch-prototype', 'capacity': 8, 'outer_mm': [147., 101.6, 26.],
              'loose_retainer_frames': 0, 'internal_parts': 3, 'required_fasteners': 0,
              'reference_pcb_blank_short_edge_mm': 2., 'illustrative_release_travel_mm': 1.5,
              'physical_tested': False, 'sliced': False, 'force_or_fatigue_verified': False,
              'checks': counts, 'plates': reports,
              'unchanged_v3_sha256': {name+'.stl': hashlib.sha256((out/(name+'.stl')).read_bytes()).hexdigest()
                                     for name in parts if name not in static}}
    (out/'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    from preview_simple_trays import preview
    preview(out, parts, static, leaves, plates, module)
    print(json.dumps(report, indent=2))
    return parts, static, leaves, plates


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, default=ROOT/'models/v2-retention')
    parser.add_argument('--v3-models', type=Path, default=ROOT/'models/v3')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/v3-simple')
    args = parser.parse_args()
    build(args.models.resolve(), args.v3_models.resolve(), args.output_dir.resolve())
