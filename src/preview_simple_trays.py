"""Mesh-derived illustrations of the integral-latch prototype."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_v3 as v3


def preview(out, parts, fixed, leaves, plates, module):
    im = Image.new('RGB', (1500, 1070), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=26)
    small = ImageFont.load_default(size=20)
    projection = np.array([[.85, -.5, 0], [.23, .39, -.891], [.445, .757, .476]])
    def render(items, cx, cy, scale, center):
        pixels = np.asarray(im).copy()
        depth = np.full((im.height, im.width), -np.inf)
        for solid, color in items:
            mesh = v3.meshof(solid)
            p = (mesh.vertices-np.asarray(center))@projection.T
            xy = p[:, :2]*scale+[cx, cy]
            for i, tri in enumerate(mesh.faces):
                normal = mesh.face_normals[i]
                if normal@projection[2] <= 0:
                    continue
                poly, zz = xy[tri], p[tri, 2]
                xmin, xmax = max(0, int(np.floor(poly[:, 0].min()))), min(im.width-1, int(np.ceil(poly[:, 0].max())))
                ymin, ymax = max(0, int(np.floor(poly[:, 1].min()))), min(im.height-1, int(np.ceil(poly[:, 1].max())))
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
                shade = .72+.25*max(0, float(normal@np.array([-.3, -.4, .866])))
                pixels[ymin:ymax+1, xmin:xmax+1][hit] = (np.array(color)*shade).astype(np.uint8)
        im.paste(Image.fromarray(pixels))
    blue, gold, green = (100, 151, 180), (231, 169, 70), (105, 164, 126)
    draw.text((35, 22), 'V3-S: 8 RDIMMs, three trays, ZERO loose retainer frames', font=font, fill='#172c40')
    draw.text((35, 64), 'Integral tabs and fixed end slots replace the separate frames. Same 147 x 101.6 x 26 mm shell.', font=small, fill='#445566')
    name = 'tray-top-3'
    render([(fixed[name], blue)]+[(leaf, gold) for _, leaf in leaves[name]], 495, 315, 5.2, [73.5, 50.8, 0])
    for i, txt in enumerate(['1. Slide open the cover.', '2. Lift out the required tray.', '3. Release its tab to remove RAM.', '',
                              'To load: tuck one end into the slot,', 'hold the tab aside, lower the RAM,', 'then release the tab.', '',
                              'No loose frames. No internal screws.']):
        draw.text((970, 160+32*i), txt, font=small, fill='#172c40')
    draw.text((35, 495), 'Gold highlights the integral flexures; these are NOT separate printed parts.', font=small, fill='#445566')
    name = 'test-tray-1'
    ram = module(133.8, 31.4, 1.37, 6.6, 35.1)
    draw.text((35, 557), 'Fixed PCB-edge slot', font=font, fill='#172c40')
    crop = v3.box((12., 22., 9.), (0, 39., 0))
    render([(fixed[name]^crop, blue), (ram^crop, green)], 335, 805, 20., [6, 50, 2])
    draw.text((780, 557), 'Outward release tab (arrow on top)', font=font, fill='#172c40')
    crop = v3.box((12., 24., 9.), (135., 36., 0))
    render([(fixed[name]^crop, blue), (ram^crop, green)]+[(leaf^crop, gold) for _, leaf in leaves[name]],
           1110, 805, 20., [141, 48, 2])
    draw.text((35, 988), 'Actual CAD meshes; green is the reference RAM envelope. Printing, release force and fatigue remain unverified.', font=small, fill='#445566')
    draw.text((35, 1021), 'Remove the tray before releasing tabs. Keep it level and hold the RAM during release.', font=small, fill='#445566')
    im.save(out/'simple-tray-preview.png')

    im = Image.new('RGB', (1250, 800), '#f4f6f8')
    draw = ImageDraw.Draw(im)
    draw.text((30, 20), 'V3-S: one test plate; complete set uses TWO plates', font=font, fill='#172c40')
    for k, (name, label) in enumerate([('first-test-all', 'Test: gauge + integral tray + mechanism coupons'),
                                      ('plate-2-all-trays', 'Full plate 2: all three trays')]):
        left, top, scale = 30+620*k, 135, 2.2
        draw.text((left, 88), label, font=small, fill='#172c40')
        draw.rectangle((left, top, left+256*scale, top+256*scale), fill='white', outline='#81909e', width=2)
        for i, mesh in enumerate(plates[name]):
            color = ('#93b9cc', '#a4c8b4', '#e8c88f')[i % 3]
            for tri in mesh.faces:
                draw.polygon([(left+x*scale, top+(256-y)*scale) for x, y in mesh.vertices[tri, :2]], fill=color)
    draw.text((30, 730), '100% scale; print by layer. Full plate 1 is the unchanged v3 shell + lid. Check local supports and slit paths.', font=small, fill='#445566')
    im.save(out/'simple-plates.png')
