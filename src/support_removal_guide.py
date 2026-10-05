"""CAD / G-code derived keep-versus-remove views. Does not edit user photos."""
from pathlib import Path
import json
import numpy as np
import trimesh
import manifold3d as m
from PIL import Image, ImageDraw, ImageFont
import build_v3 as v3
from audit_v3_2_toolpaths import parse

ROOT = Path(__file__).resolve().parents[1]


def render(items, camera, size=(680, 270)):
    camera = np.asarray(camera, dtype=float); camera /= np.linalg.norm(camera)
    right = np.cross([0, 0, 1], camera); right /= np.linalg.norm(right)
    down = np.cross(right, camera)
    projection = np.array([right, down, camera])
    points = np.concatenate([mesh.vertices for mesh, _ in items]) @ projection.T
    middle = (points.min(0)+points.max(0))/2
    scale = min((size[0]-35)/np.ptp(points[:, 0]), (size[1]-30)/np.ptp(points[:, 1]))
    pixels = np.full((size[1], size[0], 3), 250, dtype=np.uint8)
    depth = np.full((size[1], size[0]), -np.inf)
    for mesh, color in items:
        p = mesh.vertices @ projection.T-middle
        xy = p[:, :2]*scale+np.array(size)/2
        for normal, tri in zip(mesh.face_normals, mesh.faces):
            if normal @ camera <= 0: continue
            poly, zz = xy[tri], p[tri, 2]
            xmin, ymin = np.maximum(0, np.floor(poly.min(0)).astype(int))
            xmax, ymax = np.minimum(np.array(size)-1, np.ceil(poly.max(0)).astype(int))
            if xmin > xmax or ymin > ymax: continue
            xx, yy = np.meshgrid(np.arange(xmin, xmax+1)+.5, np.arange(ymin, ymax+1)+.5)
            (x0,y0),(x1,y1),(x2,y2) = poly
            den = (y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
            if abs(den) < 1e-10: continue
            a = ((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
            b = ((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
            c = 1-a-b
            z = a*zz[0]+b*zz[1]+c*zz[2]
            target = depth[ymin:ymax+1, xmin:xmax+1]
            hit = (a>=0)&(b>=0)&(c>=0)&(z>target)
            target[hit] = z[hit]
            pixels[ymin:ymax+1, xmin:xmax+1][hit] = np.array(color)*(.65+.3*max(0, normal@camera))
    return Image.fromarray(pixels)


def main():
    records = json.loads((ROOT/'models/v3.2-rc1/verification.json').read_text())['plate_records']
    record = next(r for r in records if r['stem'].endswith('plate-0-checks'))
    transforms = {p['part']: np.array(p['assembly_to_plate']) for p in record['poses']}
    offsets = {'latch-test-base': [35,65,0], 'test-tray-1': [45,140,0], 'bottom-recess-test': [190,65,0]}
    segs = parse(ROOT/'build/v3.2-rc1-recheck/0-checks/plate_1.gcode')
    supports = segs[segs[:, 7] == 1]
    views = [
        ('A  Shell latch / front', 'latch-test-base', [33,0,19.2], [86,10,26], [.12,-1,.65], 'KEEP the thin top beam and raised tooth.'),
        ('B  Tray fixed slot / inside', 'test-tray-1', [1.9,40,0], [12,61,6.8], [1,-.35,.7], 'KEEP the upper lip AND the lower PCB shelf.'),
        ('C  Tray release tab / outside', 'test-tray-1', [136,37,0], [145.1,58.5,6.8], [1,-.4,1.], 'KEEP the long thin arm, tooth and arrow paddle.'),
        ('D  Recess coupon / UNDERSIDE', 'bottom-recess-test', [1.9,18.1,0], [11.9,66.1,6.8], [.9,-.4,-.8], 'Turn over: remove support inside the bottom recess.'),
    ]
    im = Image.new('RGB', (1440, 1510), '#fafafa'); d = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=25); small = ImageFont.load_default(size=18)
    d.text((30,15), 'v3.2 RC1  |  Support removal map', font=font, fill='#193247')
    d.text((30,52), 'BLUE = KEEP all model material     ORANGE = REMOVE slicer supports', font=small, fill='#193247')
    d.text((30,82), 'CAD + nominal G-code support paths; colors are illustrative. Not a photo of a cleaned print.', font=small, fill='#526578')
    blue, orange = (72,139,180), (235,127,47)
    for i,(title,name,lo,hi,camera,note) in enumerate(views):
        mesh = trimesh.load_mesh(ROOT/'models/v3.2-rc1'/(name+'.stl'))
        mesh.apply_translation(np.array(offsets[name])-transforms[name][:3,3])
        solid = m.Manifold(m.Mesh(mesh.vertices.astype(np.float32),mesh.faces.astype(np.uint32)))
        model = v3.meshof(solid ^ v3.box(np.array(hi)-lo,lo))
        local = supports.copy(); shift = transforms[name][:3,3]
        local[:,[0,2]] -= shift[0]; local[:,[1,3]] -= shift[1]; local[:,4] -= shift[2]
        blocks = []
        for x,y,qx,qy,z,w,h,_ in local:
            mid = np.array([(x+qx)/2,(y+qy)/2,z-h/2])
            if not np.all(mid>=lo) or not np.all(mid<=hi): continue
            length = np.hypot(qx-x,qy-y)
            if length < 1e-6: continue
            block = trimesh.creation.box(extents=[length,w,h])
            block.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(qy-y,qx-x),[0,0,1]))
            block.apply_translation(mid); blocks.append(block)
        support = trimesh.util.concatenate(blocks)
        top = 123+i*344
        d.text((30,top),title,font=font,fill='#193247')
        im.paste(render([(model,blue),(support,orange)],camera),(20,top+32))
        im.paste(render([(model,blue)],camera),(740,top+32))
        d.text((30,top+300),'Before: locate orange supports',font=small,fill='#a44b0b')
        d.text((750,top+300),'After: '+note,font=small,fill='#193247')
    out = ROOT/'build/v3.2-rc1-removal-guide'; out.mkdir(exist_ok=True)
    im.save(out/'support-removal-map.png')
    print(out/'support-removal-map.png')


if __name__ == '__main__': main()
