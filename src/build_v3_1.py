"""Versioned v3.1 distribution. Freeze v3-S geometry; provide two full plates.

3MFs contain geometry only, no printer/material/support configuration or G-code.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import manifold3d as m
from PIL import Image, ImageDraw, ImageFont
import build_simple_trays as simple
from check_bambu_v3 import read_mesh, components
from preview_simple_trays import preview

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.1'
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'


def as_solid(mesh):
    return m.Manifold(m.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))


def export_3mf(path, mesh):
    # One build object holds all disconnected pieces at their arranged positions.
    ET.register_namespace('', NS)
    tag = lambda s: '{'+NS+'}'+s
    root = ET.Element(tag('model'), {'unit': 'millimeter', 'xml:lang': 'en-US'})
    ET.SubElement(root, tag('metadata'), {'name': 'Title'}).text = path.stem
    ET.SubElement(root, tag('metadata'), {'name': 'Description'}).text = 'RDIMM HDD case v3.1; geometry only; print by layer at 100%; not sliced.'
    resources = ET.SubElement(root, tag('resources'))
    obj = ET.SubElement(resources, tag('object'), {'id': '1', 'type': 'model', 'name': path.stem})
    element = ET.SubElement(obj, tag('mesh'))
    vertices = ET.SubElement(element, tag('vertices'))
    for v in mesh.vertices:
        ET.SubElement(vertices, tag('vertex'), dict(zip(('x', 'y', 'z'), (f'{a:.8f}' for a in v))))
    triangles = ET.SubElement(element, tag('triangles'))
    for face in mesh.faces:
        ET.SubElement(triangles, tag('triangle'), dict(zip(('v1', 'v2', 'v3'), map(str, face))))
    build = ET.SubElement(root, tag('build'))
    ET.SubElement(build, tag('item'), {'objectid': '1'})
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        def write(name, data):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
        write('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        write('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/></Relationships>')
        write('3D/3dmodel.model', ET.tostring(root, encoding='utf-8', xml_declaration=True))
    restored = read_mesh(path)
    assert restored.is_watertight and restored.is_winding_consistent
    assert np.allclose(restored.bounds, mesh.bounds, atol=.00001)
    assert abs(restored.volume-mesh.volume) < .001
    assert components(restored) == components(mesh)


def build(models, v3models, out):
    parts, fixed, leaves, plates = simple.build(models, v3models, out)
    preview(out, parts, fixed, leaves, plates, simple.module, version='V3.1')
    report = json.loads((out/'verification.json').read_text())
    report.update(version=VERSION, variant='v3.1-integral-latch-prototype',
                  previous_design='v3-S, cc9afd5bc0aef89c80ddbaa6241953b412729875',
                  geometry_changed_from_v3_simple=False)
    (out/'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    names = [('plate-1-body-pin-clearance-lid', 'rdimm-v3.1-plate-1-pin-clearance', ['body-pin-clearance', 'lid-slide']),
             ('plate-1-body-thread-pilot-lid', 'rdimm-v3.1-plate-1-thread-pilot', ['body-thread-pilot', 'lid-slide']),
             ('plate-2-all-trays', 'rdimm-v3.1-plate-2-all-trays', ['tray-bottom-2', 'tray-middle-3', 'tray-top-3'])]
    def place(name, x, y, turn=False):
        mesh = trimesh.load_mesh(out/(name+'.stl'))
        if turn:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [0, 0, 1]))
        mesh.apply_translation(-mesh.bounds[0]+np.array([x, y, 0.]))
        return mesh
    batch_layouts = {
        'batch-a-body-lid-bottom': [place('body-pin-clearance', 17.8, 22.4), place('lid-slide', 19.6, 132.),
                                  place('tray-bottom-2', 172.8, 56.6, True)],
        'batch-b-middle-top-2sets': [place('tray-middle-3', 5.5, 152.7), place('tray-top-3', 152.7, 107.3, True),
                                   place('tray-middle-3', 107.3, 5.5), place('tray-top-3', 5.5, 5.5, True)]}
    for name, meshes in batch_layouts.items():
        margin, gap_min = (8., 8.) if name.startswith('batch-a') else (5.5, 4.)
        for i, mesh in enumerate(meshes):
            assert mesh.bounds[0, :2].min() >= margin-.0001 and mesh.bounds[1, :2].max() <= 256-margin+.0001
            for other in meshes[:i]:
                gap = np.maximum(0, np.maximum(mesh.bounds[0, :2]-other.bounds[1, :2], other.bounds[0, :2]-mesh.bounds[1, :2]))
                assert np.linalg.norm(gap) >= gap_min-.0001
        trimesh.util.concatenate(meshes).export(out/(name+'.stl'))
    names += [('batch-a-body-lid-bottom', 'rdimm-v3.1-batch-a-body-lid-bottom', ['body-pin-clearance', 'lid-slide', 'tray-bottom-2']),
              ('batch-b-middle-top-2sets', 'rdimm-v3.1-batch-b-middle-top-2sets', ['tray-middle-3', 'tray-top-3', 'tray-middle-3', 'tray-top-3'])]
    records = []
    for source, name, objects in names:
        shutil.copyfile(out/(source+'.stl'), out/(name+'.stl'))
        mesh = trimesh.load_mesh(out/(name+'.stl'))
        assert mesh.is_watertight and mesh.is_winding_consistent and components(mesh) == len(objects)
        assert abs(mesh.bounds[0, 2]) < .0001
        export_3mf(out/(name+'.3mf'), mesh)
        records.append({'plate': name, 'parts': objects, 'pieces': len(objects), 'bounds_mm': mesh.bounds.tolist(),
                        'files': {ext: {'file': name+'.'+ext, 'sha256': hashlib.sha256((out/(name+'.'+ext)).read_bytes()).hexdigest()}
                                  for ext in ('stl', '3mf')}})
    part_names = ['body-pin-clearance', 'lid-slide', 'tray-bottom-2', 'tray-middle-3', 'tray-top-3']
    areas = {}
    for name in part_names:
        mesh = trimesh.load_mesh(out/(name+'.stl'))
        outline = m.CrossSection(as_solid(mesh).project().to_polygons(), m.FillRule.Positive)
        areas[name] = outline.area()
    area_sum = sum(areas.values())
    assert area_sum > 256**2, 'Reassess the minimum plate count'
    manifest = {'version': VERSION, 'release_tag': 'v3.1', 'status': 'prototype awaiting physical validation',
                'units': 'mm', 'bed_mm': [256, 256], 'scale_percent': 100, 'print_sequence': 'by layer',
                'case_plate_count': 2, 'case_piece_count': 5, 'capacity': 8, 'outer_mm': [147, 101.6, 26],
                'minimum_plate_count_basis': 'fixed flat orientations, no vertical stacking, non-overlapping XY projections',
                'part_projection_area_mm2': areas, 'total_projection_area_mm2': area_sum, 'bed_area_mm2': 256**2,
                'single_flat_plate_impossible_by_area': True,
                'default_first_plate': names[0][1], 'alternate_first_plate': names[1][1],
                'second_plate': names[2][1], 'choose_one_format_per_plate': True,
                'batch_10_sets': {'print_counts': {names[3][1]: 10, names[4][1]: 5}, 'print_jobs': 15,
                                  'not_a_global_minimum_proof': True, 'batch_b_gap_mm': 4, 'batch_b_bed_margin_mm': 5.5},
                'sliced': False, 'printer_profile_embedded': False, 'plates': records}
    (out/'release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    plate_preview(out, names)
    plate_preview(out, names, batch=True)
    print(json.dumps({'version': VERSION, 'minimum_flat_plates': 2, 'projection_area_mm2': area_sum}, indent=2))


def plate_preview(out, names, batch=False):
    im = Image.new('RGB', (1440, 920), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    title, font, small = (ImageFont.load_default(size=n) for n in (27, 21, 18))
    draw.text((30, 23), 'RDIMM HDD CASE v3.1 - '+('TEN SETS: 15 PRINT JOBS' if batch else 'COMPLETE SET: TWO P2S PLATES'), font=title, fill='#172c40')
    draw.text((30, 70), 'Print batch A ten times and batch B five times. Validate one complete set first.' if batch else '8 DIMMs | 147 x 101.6 x 26 mm | 5 printed pieces | no loose retainer frames', font=font, fill='#445566')
    panels = [(3, 'A x 10: body + lid + bottom tray'), (4, 'B x 5: two middle/top pairs')] if batch else [(0, '1: pin-clearance shell + sliding lid'), (2, '2: bottom, middle and top trays')]
    for k, (idx, label) in enumerate(panels):
        source, _, _ = names[idx]
        mesh = trimesh.load_mesh(out/(source+'.stl'))
        meshes = as_solid(mesh).decompose()
        left, top, scale = 30+715*k, 155, 2.55
        draw.text((left, 116), label, font=font, fill='#172c40')
        draw.rectangle((left, top, left+256*scale, top+256*scale), fill='white', outline='#81909e', width=2)
        for i, s in enumerate(meshes):
            contours = m.CrossSection(s.project().to_polygons(), m.FillRule.Positive).to_polygons()
            for poly in sorted(contours, key=lambda p: -abs(np.sum(p[:, 0]*np.roll(p[:, 1], -1)-p[:, 1]*np.roll(p[:, 0], -1)))):
                signed = np.sum(poly[:, 0]*np.roll(poly[:, 1], -1)-poly[:, 1]*np.roll(poly[:, 0], -1))
                points = [(left+x*scale, top+(256-y)*scale) for x, y in poly]
                draw.polygon(points, fill=('#93b9cc', '#a4c8b4', '#e8c88f')[i % 3] if signed>0 else 'white', outline='#516d7b')
    draw.text((30, 843), 'Import ONE STL or 3MF per plate. Keep 100% scale, flat orientations and print by layer.', font=font, fill='#445566')
    draw.text((30, 879), 'Batch B: 4 mm gaps, 5.5 mm bed margins. Check brim/support clearance; count each printed tray pair.' if batch else 'Thread-pilot shell is an alternate plate 1. Supports/material settings still require slicing; no G-code is included.', font=small, fill='#445566')
    im.save(out/('v3.1-batch-10.png' if batch else 'v3.1-full-plates.png'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, default=ROOT/'models/v2-retention')
    parser.add_argument('--v3-models', type=Path, default=ROOT/'models/v3')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/v3.1')
    args = parser.parse_args()
    build(args.models.resolve(), args.v3_models.resolve(), args.output_dir.resolve())
