"""Concave floor fillets and preserved HDD mounting voids (millimetres)."""
import build_v3 as v3


def long_strip(radius):
    v=v3
    # Section is the concave floor/wall fillet: square outside a quarter circle.
    slab=v.box((v.L-3.2,radius+.01,radius+.01),(1.6,1.59,3.99))
    cutter=v3.m.Manifold.cylinder(v.L,radius,radius,circular_segments=64).rotate((0,90,0)).translate((0,1.6+radius,4+radius))
    return slab-cutter


def fillets(radius,all_walls=False):
    v=v3
    s=long_strip(radius)
    s+=s.mirror((0,1,0)).translate((0,v.W,0))
    if all_walls:
        slab=v.box((radius+.01,v.W-3.2,radius+.01),(1.59,1.6,3.99))
        cutter=v3.m.Manifold.cylinder(v.W,radius,radius,circular_segments=64).rotate((-90,0,0)).translate((1.6+radius,0,4+radius))
        q=slab-cutter
        s+=q+q.mirror((1,0,0)).translate((v.L,0,0))
    return s


def mount_voids(pin):
    v=v3;r=1.8 if pin else 1.35
    holes=v3.m.Manifold()
    for x in v.SIDE_X:
        holes+=v.cyl(5.8,r,(x,-.1,6.35),rot=(-90,0,0))
        holes+=v.cyl(5.8,r,(x,v.W+.1,6.35),rot=(90,0,0))
    for x in v.BOTTOM_X:
        for y in v.BOTTOM_Y:holes+=v.cyl(5.4,r,(x,y,-.1))
    return holes


