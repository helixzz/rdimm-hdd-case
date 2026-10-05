"""Pack unchanged v2 meshes for a 256 mm P2S bed. Geometry only; no G-code."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

import manifold3d as m
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--models', type=Path, default=ROOT / 'models/v2')
parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/plates-v2')
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
BED = 256.0
GAP = 8.0
NAMESPACE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'


def load(name):
    mesh = trimesh.load_mesh(args.models / (name + '.stl'))
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert np.isclose(mesh.bounds[0, 2], 0, atol=1e-5)
    return mesh


def solid(mesh):
    return m.Manifold(m.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                            np.asarray(mesh.faces, dtype=np.uint32)))


def place(name, x, y, rotate=False):
    mesh = load(name)
    if rotate:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
    mesh.apply_translation(-mesh.bounds[0] + np.array([x, y, 0]))
    return name, mesh


def export_3mf(path, items):
    # One build assembly preserves the relative positions when imported.
    ET.register_namespace('', NAMESPACE)
    tag = lambda name: '{' + NAMESPACE + '}' + name
    model = ET.Element(tag('model'), {'unit': 'millimeter', 'xml:lang': 'en-US'})
    ET.SubElement(model, tag('metadata'), {'name': 'Title'}).text = path.stem
    resources = ET.SubElement(model, tag('resources'))
    for ident, (name, mesh) in enumerate(items, 1):
        obj = ET.SubElement(resources, tag('object'), {'id': str(ident), 'type': 'model', 'name': name})
        element = ET.SubElement(obj, tag('mesh'))
        vertices = ET.SubElement(element, tag('vertices'))
        for v in mesh.vertices:
            ET.SubElement(vertices, tag('vertex'), dict(zip(('x', 'y', 'z'), (f'{a:.8f}' for a in v))))
        triangles = ET.SubElement(element, tag('triangles'))
        for face in mesh.faces:
            ET.SubElement(triangles, tag('triangle'), dict(zip(('v1', 'v2', 'v3'), map(str, face))))
    assembly = ET.SubElement(resources, tag('object'), {'id': str(len(items)+1), 'type': 'model', 'name': path.stem})
    components = ET.SubElement(assembly, tag('components'))
    for ident in range(1, len(items)+1):
        ET.SubElement(components, tag('component'), {'objectid': str(ident)})
    build = ET.SubElement(model, tag('build'))
    ET.SubElement(build, tag('item'), {'objectid': str(len(items)+1)})
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        archive.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/></Relationships>')
        archive.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
    # Read back every serialized triangle and coordinate, not just ZIP integrity.
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        document = ET.fromstring(archive.read('3D/3dmodel.model'))
        for (_, source), obj in zip(items, document.find(tag('resources')).findall(tag('object'))):
            element = obj.find(tag('mesh'))
            vertices = [[float(v.get(k)) for k in ('x', 'y', 'z')] for v in element.find(tag('vertices'))]
            faces = [[int(f.get(k)) for k in ('v1', 'v2', 'v3')] for f in element.find(tag('triangles'))]
            assert np.allclose(vertices, source.vertices, atol=1e-7)
            assert np.array_equal(faces, source.faces)


layouts = {}
for variant in ('pilot', 'side-inserts'):
    layouts['plate-1-' + variant] = [
        place('body-' + variant, 17.8, 22.4),
        place('lid', 17.8, 132.0),
        place('tray-bottom-2', 172.8, 56.6, rotate=True),
    ]
layouts['plate-2-middle-top'] = [place('tray-middle-3', 56.6, 26.2), place('tray-top-3', 56.6, 132.0)]
layouts['optional-test-plate'] = [
    *(place('fit-coupon-1-slot-print-3', 56.6, 43.0+i*41) for i in range(3)),
    place('stack-coupon-cap', 59.05, 166.0),
    place('side-insert-coupon', 108.0, 207.0),
]

reports = []
for name, items in layouts.items():
    distances = []
    for i, (part, mesh) in enumerate(items):
        assert (mesh.bounds[0, :2] >= 8-1e-5).all()
        assert (mesh.bounds[1, :2] <= BED-8+1e-5).all()
        assert np.isclose(mesh.bounds[0, 2], 0, atol=1e-5)
        assert np.allclose(np.sort(mesh.extents), np.sort(load(part).extents), atol=1e-5)
        for _, other in items[:i]:
            separation = np.maximum(0, np.maximum(mesh.bounds[0, :2]-other.bounds[1, :2], other.bounds[0, :2]-mesh.bounds[1, :2]))
            distance = float(np.linalg.norm(separation))
            assert distance >= GAP-1e-4, (name, distance)
            distances.append(distance)
    combined = trimesh.util.concatenate([mesh for _, mesh in items])
    combined.export(OUT / (name + '.stl'))
    restored = trimesh.load_mesh(OUT / (name + '.stl'))
    assert restored.is_watertight and restored.is_winding_consistent
    assert len(solid(restored).decompose()) == len(items)
    assert np.allclose(restored.bounds, combined.bounds, atol=2e-5)
    assert np.isclose(restored.volume, combined.volume, rtol=1e-6)
    export_3mf(OUT / (name + '.3mf'), items)
    reports.append({'plate': name, 'objects': [n for n, _ in items],
                    'bounds_mm': combined.bounds.tolist(),
                    'minimum_bbox_gap_mm': min(distances),
                    'minimum_bed_edge_margin_mm': float(min(combined.bounds[0, :2].min(), (BED-combined.bounds[1, :2]).min())),
                    'shell_count': len(items), 'roundtrip_verified': True})

case_parts = ['body-pilot', 'lid', 'tray-bottom-2', 'tray-middle-3', 'tray-top-3']
areas = {name: solid(load(name)).project().area() for name in case_parts}
area_sum = sum(areas.values())
assert area_sum > BED*BED, 'Reassess the two-plate lower bound if geometry changes'
report = {'bed_mm': [BED, BED], 'part_gap_mm': GAP, 'case_plate_count': 2,
          'optional_test_plate_separate': True, 'source_projection_area_mm2': areas,
          'total_projection_area_mm2': area_sum, 'bed_area_mm2': BED*BED,
          'single_flat_plate_impossible_by_area': True, 'plates': reports,
          'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.models.glob('*.stl'))},
          'printer_profile_embedded': False, 'sliced': False, 'physical_tested': False}
(OUT/'layout-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

im = Image.new('RGB', (1500,930), '#f4f6f8')
draw = ImageDraw.Draw(im)
title = ImageFont.load_default(size=29)
font = ImageFont.load_default(size=21)
small = ImageFont.load_default(size=17)
draw.text((35,25), 'RDIMM v2 - complete case in two P2S plates', font=title, fill='#172c40')
draw.text((35,70), '256 x 256 mm bed | 8 mm part gaps | all parts flat | lid stays exterior-face-down', font=font, fill='#445566')
colors = ['#8ab3cd', '#9ac9b4', '#edc894']
for left, key, label in [(40, 'plate-1-pilot', 'Plate 1: body + lid + bottom tray'), (790, 'plate-2-middle-top', 'Plate 2: middle + top trays')]:
    top, scale = 160, 2.5
    draw.text((left,120),label,font=font,fill='#172c40')
    draw.rectangle((left,top,left+640,top+640),fill='white',outline='#7f8a96',width=2)
    for grid in range(32,256,32):
        draw.line((left+grid*scale,top,left+grid*scale,top+640),fill='#e9edef')
        draw.line((left,top+grid*scale,left+640,top+grid*scale),fill='#e9edef')
    for i,(part,mesh) in enumerate(layouts[key]):
        contours = solid(mesh).project().to_polygons()
        for poly in sorted(contours,key=lambda p: -abs(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))):
            signed = np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1))
            points=[(left+x*scale,top+(256-y)*scale) for x,y in poly]
            draw.polygon(points,fill=colors[i] if signed>0 else 'white',outline='#516d7b')
        x,y=mesh.bounds[:,:2].mean(axis=0)
        draw.text((left+x*scale-9,top+(256-y)*scale-12),str(i+1),font=title,fill='#172c40')
    names=' | '.join(f'{i+1}: {n}' for i,(n,_) in enumerate(layouts[key]))
    draw.text((left,822),names,font=small,fill='#445566')
draw.text((35,885),'Side-insert body: use alternate plate 1. Test coupons are on a separate optional plate.',font=font,fill='#445566')
im.save(OUT/'plate-layout.png')
print(json.dumps({'total_projection_mm2':area_sum,'bed_area_mm2':BED*BED,'plates':[p['plate'] for p in reports]},indent=2))
