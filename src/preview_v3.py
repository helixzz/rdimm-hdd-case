"""Render the actual v3 meshes and plate layouts, not illustrative mockups."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def preview(out, parts, assembly, plates, meshof, box, opposite):
    im = Image.new('RGB', (1500, 1120), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=25)
    small = ImageFont.load_default(size=19)
    projection = np.array([[.78, -.63, 0], [.33, .41, -.85], [.535, .665, .519]])

    def render(items, cx, cy, scale, center):
        pixels = np.asarray(im).copy()
        depth = np.full((im.height, im.width), -np.inf)
        for solid, color in items:
            mesh = meshof(solid)
            p = (mesh.vertices-np.asarray(center))@projection.T
            xy = p[:, :2]*scale+[cx, cy]
            for i, tri in enumerate(mesh.faces):
                normal = mesh.face_normals[i]
                if normal@projection[2] <= 0:
                    continue
                poly, zz = xy[tri], p[tri, 2]
                xmin = max(0, int(np.floor(poly[:, 0].min())))
                xmax = min(im.width-1, int(np.ceil(poly[:, 0].max())))
                ymin = max(0, int(np.floor(poly[:, 1].min())))
                ymax = min(im.height-1, int(np.ceil(poly[:, 1].max())))
                if xmin > xmax or ymin > ymax:
                    continue
                xx, yy = np.meshgrid(np.arange(xmin, xmax+1)+.5, np.arange(ymin, ymax+1)+.5)
                (x0, y0), (x1, y1), (x2, y2) = poly
                den = (y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
                if abs(den) < 1e-10:
                    continue
                a = ((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
                b = ((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
                c = 1-a-b
                z = a*zz[0]+b*zz[1]+c*zz[2]
                target = depth[ymin:ymax+1, xmin:xmax+1]
                hit = (a >= -1e-7)&(b >= -1e-7)&(c >= -1e-7)&(z > target)
                target[hit] = z[hit]
                shade = .74+.22*max(0, float(normal@np.array([-.3, -.4, .866])))
                pixels[ymin:ymax+1, xmin:xmax+1][hit] = (np.array(color)*shade).astype(np.uint8)
        im.paste(Image.fromarray(pixels))

    blue, green, gold = (87, 124, 151), (92, 145, 132), (218, 169, 83)
    draw.text((35, 22), 'V3 prototype - tool-free loading and closure', font=font, fill='#172c40')
    draw.text((35, 62), '8 RDIMMs | 147 x 101.6 x 26 mm | no mandatory internal fasteners', font=small, fill='#445566')
    draw.text((35, 115), 'Three trays + three keyed retainer frames', font=font, fill='#172c40')
    items = [(opposite(assembly[0]), blue)]
    for tier in range(3):
        items += [(opposite(assembly[2+2*tier]).translate((0, 0, 25+23*tier)), green),
                  (opposite(assembly[3+2*tier]).translate((0, 0, 38+23*tier)), gold)]
    items += [(opposite(assembly[1]).translate((0, 0, 112)), blue)]
    render(items, 380, 815, 3.35, [73.5, 50.8, 0])
    draw.text((35, 1000), 'Lift by rigid end bars. Keep open trays horizontal.', font=small, fill='#445566')
    draw.text((35, 1030), 'The CLOSED cover captures the stack vertically.', font=small, fill='#445566')

    draw.text((805, 115), 'Press latch down, then slide cover', font=font, fill='#172c40')
    crop = box((42., 11., 8.), (42., 0, 19.))
    render([(opposite(parts['body-thread-pilot']^crop), green),
            (opposite(parts['lid-slide']^crop).translate((0, 0, 3)), blue)],
           1120, 345, 9.5, [84., 96., 20.])
    draw.text((805, 492), 'Cover shown raised for visibility; it slides in use.', font=small, fill='#445566')
    draw.text((805, 522), 'Print the latch + rail coupons before the full body.', font=small, fill='#445566')

    draw.text((805, 590), 'Connector-end bottom recess', font=font, fill='#172c40')
    crop = box((13., 58., 13.), (0, 6., 0))
    render([(opposite(parts['body-thread-pilot']^crop), blue)], 1120, 790, 6.5, [140.5, 66.6, 0])
    draw.text((805, 945), 'Target recess: 6 mm deep x 47 mm wide x 6.2 mm high.', font=small, fill='#445566')
    draw.text((805, 977), 'Backplane housing fit is NOT verified.', font=small, fill='#445566')
    draw.text((805, 1027), 'Geometry checks are not print or transport tests.', font=small, fill='#445566')
    im.save(out/'v3-preview.png')

    im = Image.new('RGB', (1600, 720), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    draw.text((30, 20), 'V3: three complete P2S plates - choose one body variant', font=font, fill='#172c40')
    names = ['plate-1-body-pin-clearance-lid', 'plate-2-middle-top', 'plate-3-bottom-frames']
    labels = ['1: body + lid', '2: middle/top trays + frame', '3: bottom tray + two frames']
    for k, name in enumerate(names):
        left, top, scale = 28+530*k, 125, 1.92
        draw.text((left, 80), labels[k], font=small, fill='#172c40')
        draw.rectangle((left, top, left+256*scale, top+256*scale), fill='white', outline='#81909e', width=2)
        for i, mesh in enumerate(plates[name]):
            color = ('#93b9cc', '#a4c8b4', '#e8c88f')[i % 3]
            for tri in mesh.faces:
                draw.polygon([(left+x*scale, top+(256-y)*scale) for x, y in mesh.vertices[tri, :2]], fill=color)
    draw.text((30, 642), '100% scale, print by layer. Plate 2: 4 mm part gaps, 5.5 mm bed margin; other plates: >= 8 mm.', font=small, fill='#445566')
    draw.text((30, 679), 'Bodies/latch coupons need local removable support under the latch beam. Inspect thin 0.4 mm frame strips.', font=small, fill='#445566')
    im.save(out/'v3-plates.png')
    test_plate_preview(out, plates['first-test-all'])
    guide_preview(out, parts, meshof)


def test_plate_preview(out, meshes):
    im = Image.new('RGB', (1250, 900), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=25)
    small = ImageFont.load_default(size=20)
    draw.text((30, 22), 'V3: all first-test parts in ONE print job', font=font, fill='#172c40')
    draw.text((30, 65), 'first-test-all.stl | 7 separate pieces | 256 x 256 mm bed', font=small, fill='#445566')
    left, top, scale = 30, 120, 2.6
    draw.rectangle((left, top, left+256*scale, top+256*scale), fill='white', outline='#81909e', width=2)
    colors = ('#93b9cc', '#a4c8b4', '#e8c88f', '#b5a2c8', '#b5a2c8', '#cfaaa2', '#cfaaa2')
    for i, mesh in enumerate(meshes):
        for tri in mesh.faces:
            draw.polygon([(left+x*scale, top+(256-y)*scale) for x, y in mesh.vertices[tri, :2]], fill=colors[i])
        x, y = mesh.bounds[1, 0]-3., mesh.bounds[1, 1]-3.
        draw.text((left+x*scale, top+(256-y)*scale), str(i+1), font=small, fill='#172c40', anchor='rt')
    labels = ['1  Empty bay-fit gauge', '2  Single-slot tray', '3  Retainer frame (TEST)',
              '4  Latch base', '5  Latch slider', '6  Rail base', '7  Rail slider']
    for i, label in enumerate(labels):
        draw.text((745, 145+43*i), label, font=small, fill='#172c40')
    for i, label in enumerate(['100% scale; print BY LAYER.', 'Preserve all part orientations.', 'Part gaps >= 10 mm.',
                               'Bed margins >= 15 mm.', 'Local latch supports: parts 1 & 4.',
                               'Check thin frame paths in slicer.', 'Geometry layout; NOT pre-sliced.']):
        draw.text((745, 490+37*i), label, font=small, fill='#445566')
    draw.text((30, 824), 'Actual mesh footprints. Colors and numbers identify parts in this preview only.', font=small, fill='#445566')
    im.save(out/'first-test-all.png')


def guide_preview(out, parts, meshof):
    """Orthographic surface views: pale areas are actual engraved recesses."""
    im = Image.new('RGB', (1500, 1030), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=25)
    small = ImageFont.load_default(size=19)

    def face(name, normal, plane, u, v, limits, origin, scale):
        lo_u, hi_u, lo_v, hi_v = limits
        panel = Image.new('RGB', (round((hi_u-lo_u)*scale), round((hi_v-lo_v)*scale)), '#dce5e9')
        pen = ImageDraw.Draw(panel)
        mesh = meshof(parts[name])
        uv = mesh.vertices@np.array([u, v]).T
        for i, tri in enumerate(mesh.faces):
            if mesh.face_normals[i]@np.array(normal) < .999:
                continue
            if not np.allclose(mesh.vertices[tri]@np.array(normal), plane, atol=.0001):
                continue
            pen.polygon([((x-lo_u)*scale, (hi_v-y)*scale) for x, y in uv[tri]], fill='#64879a')
        im.paste(panel, origin)

    draw.text((35, 22), 'V3 operation guides - engraved into the printable geometry', font=font, fill='#172c40')
    draw.text((35, 62), '0.30 mm recess | 0.55 mm stroke | 3.55 mm letters | no paint or multi-material printing required', font=small, fill='#445566')
    draw.text((35, 115), 'Cover: 1 PRESS, 2 OPEN, KEEP LEVEL', font=font, fill='#172c40')
    face('lid-slide', (0, 0, 1), 26., (1, 0, 0), (0, 1, 0), (25, 120, 0, 80), (35, 162), 6.5)
    draw.text((35, 704), 'OPEN arrow points toward the release-button edge.', font=small, fill='#445566')
    draw.text((35, 735), 'The PRESS pointer identifies the edge button.', font=small, fill='#445566')
    draw.text((790, 115), 'Matching tray / frame pairs; grip rigid ends', font=font, fill='#172c40')
    for i, (kind, n, label) in enumerate((('bottom', 2, 'Bottom: 1 BASE'), ('middle', 3, 'Middle: 2 MID'), ('top', 3, 'Top: 3 TOP'))):
        top = 190+175*i
        draw.text((790, top-35), label, font=small, fill='#445566')
        face(f'frame-{kind}-{n}', (0, 0, 1), 6.8, (0, 1, 0), (-1, 0, 0),
             (23, 60, -7.9, -1.9), (790, top), 16)
    draw.text((790, 682), 'LIFT is on thick bars, never on the thin strips.', font=small, fill='#445566')

    draw.text((35, 795), 'Fixed wall below button: PRESS down', font=small, fill='#172c40')
    face('body-pin-clearance', (0, -1, 0), 0., (1, 0, 0), (0, 0, 1),
         (62, 85, 11.5, 19.5), (35, 832), 15)
    draw.text((790, 795), 'Connector end: SATA END', font=small, fill='#172c40')
    face('body-pin-clearance', (-1, 0, 0), 0., (0, -1, 0), (0, 0, 1),
         (-45, -18, 8, 14), (790, 832), 15)
    draw.text((35, 987), 'Recesses shown light for readability. Actual contrast depends on filament, lighting and print quality.', font=small, fill='#445566')
    im.save(out/'operation-guides.png')
