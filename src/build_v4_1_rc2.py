"""Close the tops of two bottom-release windows with printable arch roofs."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import build_v4_1 as previous

base=previous.base
v=previous.v
m=previous.m
VERSION='4.1-rc2'


def upper_wall(y):
    # Y/Z opening: keep the original lower access completely clear through
    # Z=11.2. Two 45-degree shoulders meet an R1 apex (1.414 mm chord).
    cy=y+9.5;cz=20.7-math.sqrt(2)
    arc=[(cy+math.cos(a),cz+math.sin(a)) for a in np.linspace(math.pi/4,3*math.pi/4,17)]
    opening=m.CrossSection([[(y,2.2),(y+19,2.2),(y+19,11.2),*arc,(y,11.2)]])
    wall=m.CrossSection.square((19.,22.2)).translate((y,2.2))-opening
    return wall.extrude(1.6).transform([[0,0,1,145.4],[1,0,0,0],[0,1,0,0]])


def modify(p,fixed,leaves):
    p,fixed,leaves=previous.modify(p,fixed,leaves)
    for name in ('body-pin-clearance','body-thread-pilot'):
        for y,_ in leaves[name]:
            extra=upper_wall(y)
            fixed[name]+=extra
            p[name]+=extra
        p[name]=p[name].set_tolerance(.001)
    return p,fixed,leaves


def configure():
    previous.configure()
    base.VERSION=VERSION
    base.PART_MODIFIER=modify


def build(out):
    configure();base.build(out)
    p,_,leaves=base.parts()
    previous.configure();old,_,_=base.parts()
    changes={}
    access=[]
    for name,s in p.items():
        added=s-old[name];removed=old[name]-s
        assert removed.volume()<.001,(name,'removed RC1 material')
        if name.startswith('body'):
            allowed=m.Manifold()
            for y,_ in leaves[name]:
                allowed+=v.box((1.61,19.02,13.21),(145.395,y-.01,11.195))
                probe=v.box((5.9,19.,8.6),(141.1,y,2.2))
                base.clear(added,probe,'preserve lower release/support access')
                if name.endswith('clearance'):
                    access.append({'y':y,'window_width_mm':19.,'unchanged_lower_access_z_mm':[2.2,10.8],
                        'shoulder_z_mm':11.2,'apex_z_mm':20.7-math.sqrt(2)+1,
                        'top_link_min_height_mm':24.4-(20.7-math.sqrt(2)+1)})
            assert (added-allowed).volume()<.001
        else:assert added.volume()<.001,(name,'changed reusable part')
        changes[name]={'added_mm3':added.volume(),'removed_mm3':removed.volume()}
    # Explicit mixed-version check: RC1 lid/trays are the intended reusable set.
    for name,z in [('lid-slide-lift',0),('tray-middle-3',10.8),('tray-top-3',17.6)]:
        base.clear(old[name].translate((0,0,z)),p['body-pin-clearance'],'RC1 reusable part')
    configure()
    (out/'compatibility.json').write_text(json.dumps({'version':VERSION,'baseline':'4.1-rc1',
        'changes':changes,'windows':access,'apex_radius_mm':1.,'shoulder_angle_degrees':45,
        'unchanged_parts':['lid-slide-lift','tray-middle-3','tray-top-3'],
        'physical_access_verified':False,'physical_impact_verified':False,
        'limits':'Rigid motion and reserved-space checks do not prove finger ergonomics, support removal or impact strength.'},indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.1-rc2')
    build(p.parse_args().output_dir.resolve())
