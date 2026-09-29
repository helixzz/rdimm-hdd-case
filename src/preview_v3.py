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
