"""Original rounded stroke lettering; no external font or OS font dependency.

Engraved instructions, mm. Keep cuts off RAM contacts, mating guides and flexures.
"""
from functools import lru_cache
import math
import manifold3d as m

STROKE = .55
DEPTH = .30
GLYPHS = {
    '1': [[(.3, 2.3), (1., 3), (1., 0)], [(.3, 0), (1.7, 0)]],
    '2': [[(0, 2.5), (.4, 3), (1.6, 3), (2, 2.5), (2, 2), (0, 0), (2, 0)]],
    '3': [[(0, 3), (1.5, 3), (2, 2.5), (1.5, 1.5), (.6, 1.5)],
          [(1.5, 1.5), (2, 1), (2, .5), (1.5, 0), (0, 0)]],
    'A': [[(0, 0), (1, 3), (2, 0)], [(.4, 1.2), (1.6, 1.2)]],
    'B': [[(0, 0), (0, 3), (1.4, 3), (2, 2.5), (1.4, 1.5), (0, 1.5)],
          [(1.4, 1.5), (2, 1), (2, .5), (1.4, 0), (0, 0)]],
    'D': [[(0, 0), (0, 3), (1.3, 3), (2, 2.3), (2, .7), (1.3, 0), (0, 0)]],
    'E': [[(2, 3), (0, 3), (0, 0), (2, 0)], [(0, 1.5), (1.7, 1.5)]],
    'F': [[(2, 3), (0, 3), (0, 0)], [(0, 1.5), (1.7, 1.5)]],
    'I': [[(0, 3), (2, 3)], [(1, 3), (1, 0)], [(0, 0), (2, 0)]],
    'K': [[(0, 0), (0, 3)], [(2, 3), (0, 1.3), (2, 0)]],
    'L': [[(0, 3), (0, 0), (2, 0)]],
    'M': [[(0, 0), (0, 3), (1, 1.5), (2, 3), (2, 0)]],
    'N': [[(0, 0), (0, 3), (2, 0), (2, 3)]],
    'O': [[(.4, 0), (1.6, 0), (2, .4), (2, 2.6), (1.6, 3), (.4, 3), (0, 2.6), (0, .4), (.4, 0)]],
    'P': [[(0, 0), (0, 3), (1.5, 3), (2, 2.5), (2, 2), (1.5, 1.5), (0, 1.5)]],
    'R': [[(0, 0), (0, 3), (1.5, 3), (2, 2.5), (2, 2), (1.5, 1.5), (0, 1.5)], [(1, 1.5), (2, 0)]],
    'S': [[(2, 3), (.5, 3), (0, 2.5), (0, 2), (.5, 1.5), (1.5, 1.5), (2, 1), (2, .5), (1.5, 0), (0, 0)]],
    'T': [[(0, 3), (2, 3)], [(1, 3), (1, 0)]],
    'V': [[(0, 3), (1, 0), (2, 3)]],
}


def stroke(points, width=STROKE):
    shape = m.CrossSection()
    r = width/2
    for x, y in points:
        shape += m.CrossSection.circle(r, 12).translate((x, y))
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1-x0, y1-y0)
        nx, ny = -(y1-y0)*r/length, (x1-x0)*r/length
        shape += m.CrossSection([[(x0+nx, y0+ny), (x0-nx, y0-ny), (x1-nx, y1-ny), (x1+nx, y1+ny)]])
    return shape


@lru_cache(maxsize=None)
def lettering(value):
    shape = m.CrossSection()
    for i, ch in enumerate(value):
        if ch == ' ':
            continue
        for path in GLYPHS[ch]:
            shape += stroke(path).translate((3.1*i, 0))
    return shape


def down_arrow(x, tip, tail, half_width=1.9, head=2.7):
    return stroke([(x, tip+head-.2), (x, tail)])+m.CrossSection([[(x, tip), (x+half_width, tip+head), (x-half_width, tip+head)]])


def top_cut(shape, z):
    return shape.extrude(DEPTH+.1).translate((0, 0, z-DEPTH))


def apply_guides(parts):
    cuts, records = {}, []
    def add(name, cut, label, surface):
        cuts[name] = cuts.get(name, m.Manifold())+cut
        records.append({'part': name, 'mark': label, 'surface': surface})

    lid = lettering('1 PRESS').translate((63.2, 14.5))+down_arrow(73.5, 3.1, 12.)
    lid += lettering('2 OPEN').translate((64.75, 34.5))+down_arrow(73.5, 22., 32.)
    lid += lettering('KEEP LEVEL').translate((58.55, 56.5))
    lid += stroke([(61.5, 64.), (85.5, 64.), (85.5, 70.), (61.5, 70.), (61.5, 64.)])
    lid += (m.CrossSection.circle(1.2, 24)-m.CrossSection.circle(.65, 24)).translate((73.5, 67.))
    add('lid-slide', top_cut(lid, 26.), '1 PRESS / pointer; 2 OPEN / -Y arrow; KEEP LEVEL / level icon', 'exterior top')

    for name in ('body-thread-pilot', 'body-pin-clearance'):
        front = lettering('PRESS').translate((66.3, 12.5))+down_arrow(73.5, 16.8, 18.7, 1., 1.5)
        # Viewer on -Y: +X is right, +Z is up; the cutter enters Y by 0.3 mm.
        cut = front.extrude(DEPTH+.1).rotate((90, 0, 0)).translate((0, DEPTH, 0))
        add(name, cut, 'PRESS / down arrow', 'fixed front wall below latch, not on flexure')
        # Viewer on -X: -Y is right, +Z is up; avoid mirroring the text.
        end = lettering('SATA END').extrude(DEPTH+.1).transform([[0, 0, -1, DEPTH], [-1, 0, 0, 44.], [0, 1, 0, 9.2]])
        add(name, end, 'SATA END', 'connector-end outside wall')

    for kind, label, n in (('bottom', '1 BASE', 2), ('middle', '2 MID', 3), ('top', '3 TOP', 3)):
        for prefix, z in (('tray', 5.6), ('frame', 6.8)):
            name = f'{prefix}-{kind}-{n}'
            # Text runs along the narrow end bar. The right bar reads after
            # turning the box 180 degrees, and avoids the locating sockets.
            shape = lettering(label).rotate(90).translate((5.6, 26.))
            shape += lettering('LIFT').rotate(90).translate((5.6, 46.))
            cut = top_cut(shape, z)
            cut += cut.rotate((0, 0, 180)).translate((147., 101.6, 0))
            add(name, cut, label+' / LIFT, at both rigid ends', 'top of thick end rails')
    for name, z in (('retainer-test-tray', 5.6), ('retainer-test-frame', 6.8)):
        cut = top_cut(lettering('TEST').rotate(90).translate((5.6, 40.)), z)
        add(name, cut, 'TEST', 'thick end rail; lettering sample')

    result = dict(parts)
    for name, cut in cuts.items():
        before = parts[name]
        # Every mark is cut 0.3 mm into a solid face, with 0.1 mm tool overshoot.
        # Fail if a label accidentally spans a hole, a thin strip, or free air.
        removed = (before^cut).volume()
        assert abs(removed-cut.volume()*DEPTH/(DEPTH+.1)) < .01, (name, 'mark not fully on solid face', removed)
        result[name] = before-cut
        assert (result[name]-before).volume() < .0001, 'marks must never protrude'
    return result, {'depth_mm': DEPTH, 'stroke_width_mm': STROKE, 'letter_height_mm': 3.+STROKE,
                    'method': 'recessed geometry; single material; no external fonts', 'marks': records}
