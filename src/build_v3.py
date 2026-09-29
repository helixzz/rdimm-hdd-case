"""V3 engineering prototype: deeper mounts, connector clearance and sliding lid.

Input: unchanged v2-R meshes. All dimensions in mm. No fit certification.
"""
from pathlib import Path
from itertools import product
import argparse
import json
import math
import hashlib
import numpy as np
import manifold3d as m
import trimesh

ROOT = Path(__file__).resolve().parents[1]
L, W, H = 147., 101.6, 26.
BASE, PITCH, TOP = 4., 6.8, 24.4
SIDE_X = [28.4988, 70.104, 130.0988]
BOTTOM_X = [41.275, 85.725]
BOTTOM_Y = [3.175, 98.425]
KEYS = [(4.1, 61.6), (142.9, 40.)]
OPTIONAL = [(5.4, 91.6), (141.6, 10.)]


def box(size, pos=(0, 0, 0)):
    return m.Manifold.cube(size).translate(pos)


def cyl(h, r, pos, r2=-1, rot=(0, 0, 0)):
    return m.Manifold.cylinder(h, r, r2, circular_segments=48).rotate(rot).translate(pos)


def opposite(s):
    return s.rotate((0, 0, 180)).translate((L, W, 0))


def meshof(s):
    q = s.set_tolerance(.0001).to_mesh()
    mesh = trimesh.Trimesh(np.asarray(q.vert_properties)[:, :3], np.asarray(q.tri_verts), process=True)
    mesh.merge_vertices(digits_vertex=4)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    return mesh


def layout(n):
    width = n*31.8+(n-1)*.6+1.2
    y = (W-width)/2
    return width, y, [y+.6+i*32.4 for i in range(n)]


def baseline(models, name, n, keeper=False):
    mesh = trimesh.load_mesh(models/(name+'.stl'))
    if keeper:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    target = np.array([1.9, layout(n)[1], 4.5 if keeper else 0.])
    mesh.apply_translation(target-mesh.bounds[0])
    mesh.vertices = np.round(mesh.vertices, 4)
    mesh.merge_vertices()
    return m.Manifold(m.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))


def countersink(x, y, top, diameter=4.3):
    depth = (diameter-2.2)/2
    return cyl(depth, 1.1, (x, y, top-depth), diameter/2)


def end_reliefs():
    a = m.Manifold()
    for y in (10., 91.6):
        cut = box((6.55, 6.6, 8), (0, y-3.3, -.1))
        a += cut+opposite(cut)
    return a


def tray(models, name, n, bottom=False):
    a = baseline(models, name, n)
    # Fill the obsolete v2-R tie bores; no internal screw hardware remains.
    for x, y in ((4.1, 40.), (142.9, 61.6)):
        a += cyl(4.6 if bottom else 5.6, 1.21, (x, y, 1. if bottom else 0.))
    # Restore all keeper screw holes: v3 uses removable keyed retainer frames.
    width, oy, ys = layout(n)
    fastening = (42.8, 58.8) if n == 1 else (ys[0]+15.9, ys[-1]+15.9)
    for y in fastening:
        fill = cyl(4.6, .81, (4.1, y, 1.))
        a += fill+opposite(fill)
    # Seats for the two connecting strips of each one-piece frame.
    for y in (oy, oy+width-.6):
        a -= box((143.4, .7, 2.6), (1.8, y-.05, 4.3))
    for x, y in KEYS:
        a -= cyl(1.3, 1.3, (x, y, -.1))
        a += peg(x, y, 5.6, .7)
    a -= end_reliefs()
    if bottom:
        # Clearance around the body's connector-pocket roof. PCB remains at Z=7.
        a -= box((7., 47.4, 3.2), (0, 10.8, 0))
    return a


def peg(x, y, z, height=1.):
    return cyl(height-.15, 1.2, (x, y, z-.1))+cyl(.25, 1.2, (x, y, z+height-.25), 1.)


def retainer(n):
    width, oy, _ = layout(n)
    a = box((6., width, 1.2), (1.9, oy, 5.6))
    a += box((1.1, width, 1.1), (6.8, oy, 4.5))
    a += opposite(a)
    # Single-piece frame: strips join the two PCB-edge stops. They rest on
    # perimeter seats, carry no clamping load, and must not be lifting handles.
    for y in (oy+.1, oy+width-.5):
        a += box((132., .4, 2.4), (7.5, y, 4.4))
    a -= end_reliefs()
    for x, y in KEYS:
        a -= cyl(.95, 1.3, (x, y, 5.5))
    return a


def rail(length=W):
    # A 45-degree overhang prints without a horizontal support shelf.
    # Cross-section coordinates are (X,Z); extrusion becomes global Y.
    section = m.CrossSection([[(0, 24.4), (1.6, 24.4), (3.2, 26), (0, 26)]])
    return section.extrude(length).rotate((90, 0, 0)).translate((0, length, 0))


def latch_leaf():
    # Accessible at the long-side edge. Press DOWN before sliding the lid.
    # A guard carries outward shear; the thin flexure supplies Z release only.
    a = box((29., .8, 1.), (47., .8, 23.))
    a += box((5., .8, 3.), (72., .8, 23.))
    return a


def latch_guard():
    return box((7.5, .6, 4.4), (70.5, 0, 20.))


def body(pin_clearance=False, sata_y=11., full_rails=True, sata_depth=6.):
    a = box((L, W, TOP))-box((L-3.2, W-3.2, TOP+1), (1.6, 1.6, BASE))
    for x in SIDE_X:
        for y in (0., W-6.5):
            a += box((9, 6.5, 10.4), (x-4.5, y, 0))
    # Local bottom bosses deepen holes without raising the whole tray stack.
    for x in BOTTOM_X:
        for y in BOTTOM_Y:
            a += box((8, 6.35, 6.3), (x-4, 0 if y<W/2 else W-6.35, 0))
    for y in (10., 91.6):
        post = box((6.4, 6., 24.4), (0, y-3, 0))
        a += post+opposite(post)
    for y in (16.9, 83.9):
        a += box((8, .8, 3.8), (69.5, y, BASE))
    # Connector-end recess is open at X=0 and the bottom. Roof is 0.8 mm.
    a += box((sata_depth+.8, 47., 7.), (0, sata_y, 0))
    pocket = box((sata_depth+.1, 47., 6.3), (-.1, sata_y, -.1))
    a -= pocket
    diameter = 3.6 if pin_clearance else 2.7
    for x in SIDE_X:
        a -= cyl(5.8, diameter/2, (x, -.1, 6.35), rot=(-90, 0, 0))
        a -= cyl(5.8, diameter/2, (x, W+.1, 6.35), rot=(90, 0, 0))
    for x in BOTTOM_X:
        for y in BOTTOM_Y:
            a -= cyl(5.4, diameter/2, (x, y, -.1))
    for x, y in OPTIONAL:
        a += box((2.4, 4.4, .2), (4.0 if x<L/2 else L-6.4, y-2.2, TOP))
        a -= cyl(8.7, .8, (x, y, 16.))
    for x, y in KEYS:
        a += peg(x, y, BASE)
    if full_rails:
        a += rail()+opposite(rail())
    a += box((L, 1.6, 1.6), (0, 100., TOP))
    # Pocket below the flexure stays outside the module cavities (Y < 1.8).
    a -= box((31., 1.8, 7.), (47., 0, 20.))
    a += latch_leaf()+latch_guard()
    # Finger access to the rigid end bars after the lid has been slid away.
    cut = box((3.4, 8., 6.), (0, 46.8, 21.))
    a -= cut+opposite(cut)
    return a


def lid():
    section = m.CrossSection([[(1.8, 24.4), (145.2, 24.4), (143.6, 26.), (3.4, 26.)]])
    a = section.extrude(99.6).rotate((90, 0, 0)).translate((0, 99.8, 0))
    # End strips seat the retainer stack; broad center clears all components.
    a -= box((L-7.6, W, .3), (3.8, 0, TOP-.1))
    # Tooth remains ahead of this recessed edge and blocks outward sliding.
    a -= box((32., 2.1, 4.), (46.5, 0, 23.))
    for x, y in OPTIONAL:
        a -= cyl(3, 1.1, (x, y, 24.))
        a -= countersink(x, y, 26., 4.)
    # Shallow grip grooves, wholly inside the 26 mm envelope.
    for y in (6., 8., 10.):
        # Leave a central lane for the engraved pointer to the release button.
        for x in (63.5, 75.5):
            a -= box((8., .8, .35), (x, y, 25.65))
    return a


def build(models, out):
    out.mkdir(parents=True, exist_ok=True)
    parts = {
        'body-thread-pilot': body(), 'body-pin-clearance': body(True),
        'lid-slide': lid(),
        'tray-bottom-2': tray(models, 'tray-bottom-2', 2, True),
        'tray-middle-3': tray(models, 'tray-middle-3', 3),
        'tray-top-3': tray(models, 'tray-top-3', 3),
        'frame-bottom-2': retainer(2),
        'frame-middle-3': retainer(3),
        'frame-top-3': retainer(3),
        'retainer-test-tray': tray(models, 'test-tray-1', 1),
        'retainer-test-frame': retainer(1),
    }
    from operation_marks import apply_guides
    parts, guide_report = apply_guides(parts)
    parts = {name:s.set_tolerance(.0001) for name,s in parts.items()}
    assembly = [parts['body-thread-pilot'], parts['lid-slide']]
    for tier, kind in enumerate(('bottom', 'middle', 'top')):
        z = BASE+tier*PITCH
        cap = parts['frame-'+kind+('-2' if tier == 0 else '-3')]
        assembly += [parts['tray-'+kind+('-2' if tier == 0 else '-3')].translate((0, 0, z)),
                     cap.translate((0, 0, z))]
    for i, a in enumerate(assembly):
        for j, b in enumerate(assembly[:i]):
            assert (a^b).volume() < .0001, ('assembly', i, j, (a^b).volume())
    for a in assembly[1:]:
        assert (a^parts['body-pin-clearance']).volume() < .0001
    bounds = np.array([meshof(a).bounds for a in assembly])
    assert np.allclose(bounds[:, 0].min(0), [0, 0, 0], atol=.0001)
    assert np.allclose(bounds[:, 1].max(0), [L, W, H], atol=.0001)

    screws = []
    for x, y in OPTIONAL:
        screws += [cyl(8, 1., (x, y, H-8))+countersink(x, y, H, 4.)]
    for i, a in enumerate(screws):
        for b in screws[:i]:
            assert (a^b).volume() < .0001, 'screws intersect'

    # Mounting probes are tested as occupied volumes, not blind-hole depth alone.
    probes = []
    for x in SIDE_X:
        probes += [cyl(5., 1.8, (x, 0, 6.35), rot=(-90, 0, 0)),
                   cyl(5., 1.8, (x, W, 6.35), rot=(90, 0, 0))]
    for x in BOTTOM_X:
        for y in BOTTOM_Y:
            probes += [cyl(5., 1.8, (x, y, 0))]
    for probe in probes:
        for a in assembly[1:]+screws:
            assert (a^probe).volume() < .0001, 'mount intrusion'
        assert (parts['body-pin-clearance']^probe).volume() < .0001
    connector = box((6., 47., 6.2), (0, 11., 0))
    for i, a in enumerate(assembly+screws):
        assert (connector^a).volume() < .0001, ('connector recess occupied', i, (connector^a).volume())

    cases = 0
    frame_offset_cases = 0
    for tier, n in enumerate((2, 3, 3)):
        z = BASE+tier*PITCH
        for sy in layout(n)[2]:
            for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
                for bx, by, bz in product((6.5, 140.5-length), (sy+.1, sy+31.7-width), (z+3., z+4.5-pcb)):
                    module = box((length, width, pcb), (bx, by, bz))
                    module += box((length-4, width, pcb+4.2), (bx+2, by, bz-2.1))
                    for i, a in enumerate(assembly+screws+probes+[connector]):
                        assert (a^module).volume() < .0001, ('module', tier, i, bx, by, bz, (a^module).volume())
                    # Peg/socket radial clearance is 0.1 mm. Checking all four
                    # +/-0.1 XY corners is a conservative enclosing square.
                    for dx, dy in product((-.1, .1), repeat=2):
                        shifted_frame = assembly[3+2*tier].translate((dx, dy, 0))
                        assert (shifted_frame^module).volume() < .0001, 'frame travel hits module'
                        frame_offset_cases += 1
                    cases += 1
    stops = 0
    for tier, n in enumerate((2, 3, 3)):
        z = BASE+tier*PITCH
        for sy in layout(n)[2]:
            for pos in ((6.45, sy+.2, z+3.), (6.75, sy+.2, z+3.),
                        (6.6, sy+.05, z+3.), (6.6, sy+.35, z+3.),
                        (6.6, sy+.2, z+2.95), (6.6, sy+.2, z+3.18)):
                pcb = box((133.8, 31.4, 1.37), pos)
                assert sum((pcb^a).volume() for a in assembly) > .0001
                stops += 1

    # Kinematic checks exclude optional cover screws. All internal parts remain
    # present; retention against inversion is supplied by the CLOSED cover.
    cover = parts['lid-slide']
    assert (cover.translate((0, -1., 0))^assembly[0]).volume() > .01, 'missing anti-slide stop'
    assert (cover.translate((0, 1., 0))^assembly[0]).volume() > .01, 'missing rear stop'
    assert (cover.translate((0, 0, .4))^assembly[0]).volume() > .01, 'missing capture rails'
    # With no screws installed, the complete stack cannot leave vertically.
    assert (assembly[-1].translate((0, 0, .4))^cover).volume() > .01
    for tier in range(3):
        # Frame pegs constrain XY; next floor (or lid) constrains upward motion.
        frame_s = assembly[3+2*tier]
        tray_s = assembly[2+2*tier]
        for delta in ((.3, 0, 0), (-.3, 0, 0), (0, .3, 0), (0, -.3, 0)):
            assert (frame_s.translate(delta)^tray_s).volume() > .001
        ceiling = assembly[4+2*tier] if tier < 2 else cover
        assert (frame_s.translate((0, 0, .3))^ceiling).volume() > .001
    released = assembly[0]-box((31., 1.8, 7.), (47., 0, 20.))+latch_guard()
    # Illustrative bend shape, not FEA: root fixed, free end moves 2.5 mm.
    leaf = latch_leaf().warp(lambda p: (p[0], p[1], p[2]-2.5*max(0, min(1, (p[0]-47.)/30.))**2))
    assert (leaf^released).volume() < .0001, 'release hits body'
    assert (latch_leaf().translate((0, -.3, 0))^latch_guard()).volume() > .001, 'missing latch shear guard'
    released += leaf
    for i in range(102):
        moved = cover.translate((0, -float(i), 0))
        for a in [released]+assembly[2:]+screws[:-2]:
            assert (moved^a).volume() < .0001, ('cover sweep', i, (moved^a).volume())

    # A full-footprint empty fit gauge includes all mounts, connector pocket,
    # actual rails and latch; this should precede another complete RAM set.
    gauge = parts['body-pin-clearance']
    for lo, hi in ((8., 24.), (33., 36.), (47., 65.), (75., 80.), (92., 125.), (135., 140.)):
        gauge -= box((hi-lo, 78., 3.), (lo, 12., -1))
    parts['empty-fit-gauge-pin'] = gauge
    # Small sliding-rail coupon checks fit before a full-size cover/body.
    crop = box((12., 24., 8.), (0, 32., 19.))
    parts['rail-test-base'] = (parts['body-thread-pilot']^crop)+box((12., 24., 1.2), (0, 32., 19.))
    parts['rail-test-slider'] = (cover^crop)+box((2., 24., 1.6), (10., 32., 24.4))
    # Full-size flexure within a smaller captured slider, avoiding another full
    # body print merely to discover a stiff or weak latch. Coordinates preserve
    # the original root, pocket and tooth exactly.
    latch_crop = box((60., 22.6, 6.8), (33., 0, 19.2))
    test_base = assembly[0]^latch_crop
    test_base += box((60., 22.6, 1.2), (33., 0, 19.2))
    test_base += box((1.6, 22.6, 5.2), (33., 0, 19.2))
    test_base += box((1.6, 22.6, 5.2), (91.4, 0, 19.2))
    test_base += box((60., 1.6, 6.8), (33., 21., 19.2))
    test_base += rail(22.6).translate((33., 0, 0))
    test_base += rail(22.6).rotate((0, 0, 180)).translate((93., 22.6, 0))
    test_base -= box((31., 1.8, .4), (47., 0, 20.))
    section = m.CrossSection([[(34.8, 24.4), (91.2, 24.4), (89.6, 26.), (36.4, 26.)]])
    test_slider = section.extrude(20.6).rotate((90, 0, 0)).translate((0, 20.8, 0))
    test_slider -= box((32., 2.1, 4.), (46.5, 0, 23.))
    assert (test_slider^test_base).volume() < .0001
    assert (test_slider.translate((0, -1., 0))^test_base).volume() > .01
    assert (test_slider.translate((0, 0, .4))^test_base).volume() > .01
    test_released = test_base-box((31., 1.8, 7.), (47., 0, 20.))+latch_guard()
    assert (leaf^test_released).volume() < .0001
    for step in range(24):
        assert (test_slider.translate((0, -step, 0))^(test_released+leaf)).volume() < .0001
    parts['latch-test-base'] = test_base
    parts['latch-test-slider'] = test_slider
    assert (parts['retainer-test-tray']^parts['retainer-test-frame']).volume() < .0001
    coupon_cases = 0
    sy = layout(1)[2][0]
    for length, width, pcb in product((133.2, 133.8), (31.1, 31.4), (1.17, 1.37)):
        for bx, by, bz in product((6.5, 140.5-length), (sy+.1, sy+31.7-width), (3., 4.5-pcb)):
            module = box((length, width, pcb), (bx, by, bz))+box((length-4, width, pcb+4.2), (bx+2, by, bz-2.1))
            for part in ('retainer-test-tray', 'retainer-test-frame'):
                assert (parts[part]^module).volume() < .0001
            coupon_cases += 1

    records = []
    for name, s in parts.items():
        s = s.set_tolerance(.0001)
        assert len(s.decompose()) == 1, (name, 'disconnected')
        mesh = meshof(s)
        flip = name.startswith('frame-') or name in ('retainer-test-frame', 'lid-slide', 'rail-test-slider', 'latch-test-slider')
        if flip:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        shift = -mesh.bounds[0]
        mesh.apply_translation(shift)
        mesh.export(out/(name+'.stl'))
        read = trimesh.load_mesh(out/(name+'.stl'))
        assert read.is_watertight and read.is_winding_consistent, name
        assert abs(read.volume-s.volume()) < .03, (name, 'export drift')
        records.append({'part': name, 'extents_mm': read.extents.tolist(), 'volume_cm3': read.volume/1000,
                        'flip_x_180': flip, 'translation_for_print': shift.tolist(), 'single_closed_solid': True})

    plates = {}
    def place(name, x, y, turn=False):
        mesh = trimesh.load_mesh(out/(name+'.stl'))
        if turn:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]))
        mesh.apply_translation(-mesh.bounds[0]+np.array([x, y, 0.]))
        return mesh
    for kind in ('thread-pilot', 'pin-clearance'):
        plates['plate-1-body-'+kind+'-lid'] = [place('body-'+kind, 54.5, 18.2), place('lid-slide', 56.3, 129.8)]
    plates['plate-2-middle-top'] = [place('tray-middle-3', 5.5, 26.2), place('tray-top-3', 5.5, 132.),
                                    place('frame-middle-3', 152.7, 56.4, True)]
    plates['plate-3-bottom-frames'] = [place('tray-bottom-2', 19.7, 42.4),
                                      place('frame-bottom-2', 170.9, 56.4, True),
                                      place('frame-top-3', 19.7, 115.8)]
    plates['first-test-lid-mechanism'] = [place('rail-test-base', 85., 90.), place('rail-test-slider', 110., 90.),
                                         place('latch-test-base', 70., 135.), place('latch-test-slider', 145., 135.)]
    plates['first-test-retainer'] = [place('retainer-test-tray', 56.4, 75.), place('retainer-test-frame', 56.4, 125.)]
    # One print job for all three first-test groups; retain each tested print
    # orientation and leave space around the gauge/latch for local supports.
    plates['first-test-all'] = [place('empty-fit-gauge-pin', 15., 34.2),
                                place('retainer-test-tray', 15., 145.8),
                                place('retainer-test-frame', 15., 188.8),
                                place('latch-test-base', 181., 34.2),
                                place('latch-test-slider', 181., 67.2),
                                place('rail-test-base', 181., 104.2),
                                place('rail-test-slider', 211., 104.2)]
    plate_reports = []
    for name, meshes in plates.items():
        for i, mesh in enumerate(meshes):
            margin = 5.5 if name == 'plate-2-middle-top' else 8.
            minimum_gap = 4. if name == 'plate-2-middle-top' else 8.
            if name == 'first-test-all':
                margin, minimum_gap = 15., 10.
            assert mesh.bounds[0, :2].min() >= margin-.0001 and mesh.bounds[1, :2].max() <= 256-margin+.0001
            assert abs(mesh.bounds[0, 2]) < .0001
            for other in meshes[:i]:
                gap = np.maximum(0, np.maximum(mesh.bounds[0, :2]-other.bounds[1, :2], other.bounds[0, :2]-mesh.bounds[1, :2]))
                assert np.linalg.norm(gap) >= minimum_gap-.0001, (name, 'spacing')
        packed = trimesh.util.concatenate(meshes)
        packed.export(out/(name+'.stl'))
        read = trimesh.load_mesh(out/(name+'.stl'))
        assert read.is_watertight and read.is_winding_consistent
        plate_reports.append({'file': name+'.stl', 'part_count': len(meshes), 'bounds_mm': read.bounds.tolist(),
                              'minimum_part_gap_mm': minimum_gap, 'minimum_bed_margin_mm': margin})

    # Same-height, same-angle single-row arrangement, with 0.6 normal gap.
    # This is deliberately NOT an optimizer over all staggered/nested layouts.
    tilted = []
    for free_h in (20.4, 22.4):
        best = None
        for degrees in np.arange(.1, 90., .01):
            t = math.radians(degrees)
            height = 31.4*math.sin(t)+5.57*math.cos(t)
            span = 31.4*math.cos(t)+5.57*math.sin(t)
            pitch = (5.57+.6)/math.sin(t)
            if height > free_h or span > 98.4:
                continue
            count = 1+math.floor((98.4-span)/pitch)
            if best is None or (count, degrees) > (best['count'], best['angle_deg']):
                best = {'count': count, 'angle_deg': round(float(degrees), 2), 'height_mm': height,
                        'span_mm': span, 'pitch_mm': pitch}
        tilted.append({'free_height_mm': free_h, 'free_width_mm': 98.4, 'normal_gap_mm': .6, **best})
    report = {'variant': 'v3-slide-prototype', 'outer_mm': [L, W, H], 'capacity': 8,
              'operation_guides': guide_report,
              'parts': records, 'reference_module_travel_cases': cases, 'pcb_stop_checks': stops,
              'frame_xy_clearance_cases': frame_offset_cases,
              'single_slot_coupon_cases': coupon_cases,
              'lid_sweep_samples': 102, 'lid_locked_stops_checked': ['outward', 'inward', 'upward'],
              'mount_probe_count': len(probes), 'mount_probe_diameter_mm': 3.6, 'mount_probe_depth_mm': 5.,
              'blind_hole_depth_mm': {'side': 5.7, 'bottom': 5.3},
              'connector_pocket_mm': {'x': [0, 6], 'y': [11, 58], 'z': [0, 6.2]},
              'connector_pocket_is_design_target_not_universal_standard': True,
              'fasteners_required': {}, 'closed_lid_required_for_inversion_retention': True,
              'fasteners_optional': {'M2x8_countersunk_head_max_4mm': 2},
              'parallel_tilt_study': tilted, 'tilt_study_is_global_optimum': False,
              'pcb_short_edge_keepout_assumption_mm': 2,
              'physical_tested': False, 'sliced': False, 'latch_fatigue_verified': False,
              'backplane_fit_verified': False, 'thread_strength_verified': False,
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in models.glob('*.stl') if not p.name.startswith(('upgrade-', 'first-'))}}
    (out/'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (out/'plate-verification.json').write_text(json.dumps(plate_reports, indent=2), encoding='utf-8')
    from preview_v3 import preview
    preview(out, parts, assembly, plates, meshof, box, opposite)
    print(json.dumps({k:report[k] for k in ('outer_mm', 'capacity', 'reference_module_travel_cases', 'parallel_tilt_study')}, indent=2))
    return parts, assembly, screws, plates


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, default=ROOT/'models/v2-retention')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/v3')
    args = parser.parse_args()
    build(args.models.resolve(), args.output_dir.resolve())
