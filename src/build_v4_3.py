"""V4.3: floor-grown side reinforcement with a retained, rounded upper ledge."""
import argparse
import json
from pathlib import Path
import numpy as np
import build_v4_2 as previous
from floor_fillet import mount_voids, fillets

base=previous.base;v=previous.v;m=previous.m
VERSION='4.3'


def reinforcement():
    # Inner boundary rises tangentially from the floor into the ledge's face.
    # R3.5 joins floor Z4 to Y4.2 at Z7.5. R0.4 rounds the upper inner edge.
    points=[(1.59,3.99),(7.7,3.99),(7.7,4.)]
    points += [(7.7+3.5*np.cos(a),7.5+3.5*np.sin(a)) for a in np.linspace(-np.pi/2,-np.pi,33)[1:]]
    points.append((4.2,10.))
    points += [(3.8+.4*np.cos(a),10.+.4*np.sin(a)) for a in np.linspace(0,np.pi/2,17)[1:]]
    points.append((1.59,10.4))
    strip=m.CrossSection([points]).extrude(143.8).transform([[0,0,1,1.6],[1,0,0,0],[0,1,0,0]])
    return strip+strip.mirror((0,1,0)).translate((0,101.6,0))


def modify(p,fixed,leaves):
    p,fixed,leaves=previous.modify(p,fixed,leaves)
    shape=reinforcement()
    for name in ('body-pin-clearance','body-thread-pilot'):
        extra=shape-mount_voids(name.endswith('clearance'))
        p[name]=(p[name]+extra).set_tolerance(.001).simplify(.001)
        fixed[name]=(fixed[name]+extra).set_tolerance(.001).simplify(.001)
    return p,fixed,leaves


def configure():
    previous.configure();base.VERSION=VERSION;base.PART_MODIFIER=modify
    base.FLOOR_FILLET_RADIUS=0.  # One continuous profile, no tangent duplicate surface.


def build(out):
    configure();base.build(out,lid_up_probe=.55)
    new,_,_=base.parts()
    previous.configure();old,_,_=base.parts()
    changes={}
    for name in new:
        added=(new[name]-old[name]).volume();removed=(old[name]-new[name]).volume()
        assert removed<.001,(name,removed)
        if not name.startswith('body'):assert added<.001,(name,added)
        changes[name]={'added_mm3':added,'removed_mm3':removed}
    # Check material continuity and floor/ledge cross-section at a clear midspan.
    shape=reinforcement()
    assert (fillets(6)-shape).volume()<.001,'new profile must encompass v4.2 floor transition'
    for y,z in ((5.5,4.1),(3.9,8.),(3.7,10.2)):
        assert (v.box((.1,.1,.1),(60,y,z))-new['body-pin-clearance']).volume()<1e-7
    base.clear(new['body-pin-clearance'],v.box((.1,2.5,.2),(60,1.7,10.5)),'ledge must stay below tray')
    report=json.loads((out/'verification.json').read_text())
    report['status']='versioned complete release; physical testing pending'
    (out/'verification.json').write_text(json.dumps(report,indent=2))
    root=json.loads((base.ROOT/'models/v4.2/tray-root-fix.json').read_text())
    inherited={'version':VERSION,'inherited_from':'4.2','root_checks':root['root_checks'],
        'tooth_frame_clearance_checks':root['tooth_frame_clearance_checks']}
    (out/'tray-root-fix.json').write_text(json.dumps(inherited,indent=2))
    (out/'reinforcement-check.json').write_text(json.dumps({'version':VERSION,'baseline':'4.2','changes':changes,
        'floor_z_mm':4.,'floor_blend_radius_mm':3.5,'floor_blend_tangent_top_z_mm':7.5,
        'ledge_inner_y_mm':4.2,'ledge_top_z_mm':10.4,'ledge_edge_radius_mm':.4,
        'first_tray_bottom_z_mm':10.8,'vertical_gap_mm':.4,'not_a_tray_seat':True,
        'v4_2_floor_material_retained':True,'mount_voids_preserved':True,
        'unchanged_parts':['lid-slide-lift','tray-middle-3','tray-top-3'],
        'physical_strength_verified':False,'limits':'Geometry and sampled loading paths only; no stiffness, fatigue, impact or surface-quality guarantee.'},indent=2))
    configure()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.3')
    build(parser.parse_args().output_dir.resolve())
