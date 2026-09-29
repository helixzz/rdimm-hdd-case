"""V4.1 RC1: broad flat lid captures and reinforced clip roots; unprinted."""
import argparse
import json
from pathlib import Path
import build_v4_rc4 as previous
from build_v4_rc4 import base

v=base.v3
m=v.m
VERSION='4.1-rc1'
CAPTURES=[(8.,6.),(95.6,4.2)]


def shell_leaf():
    a=v.box((29.,1.6,1.2),(47.,0.,22.8))
    a+=v.box((7.,1.6,3.2),(70.,0.,22.8))
    # Concave R1 root below the spring; no notch at its fixed junction.
    fillet=v.box((1.,1.6,1.),(47.,0,21.8))
    fillet-=v.cyl(1.8,1.,(48.,-.1,21.8),rot=(-90,0,0))
    return a+fillet


def pair(s):
    return s+s.mirror((1,0,0)).translate((147,0,0))


def clip(y,z):
    # Rebuild analytic surfaces rather than duplicate engraved mesh slivers.
    a=v.box((1.,18.,6.2),(142.,y,0))
    section=m.CrossSection([[(139.4,4.5),(143.,4.5),(143.,6.2),(141.1,6.2),(139.4,4.7)]])
    a+=section.extrude(4.8).rotate((90,0,0)).translate((0,y+18.4,0))
    a+=v.box((2.2,4.8,.8),(142.1,y+13.6,5.4))
    a-=v.box((2.61,4.8,.1101),(139.39,y+13.6,4.49))
    a-=base.rc.wedge([(139.39,4.59),(139.81,4.59),(139.39,4.92)],y+13.6,4.8)
    root=v.box((1.01,1.,6.2),(142.99,y,0))
    root-=v.cyl(6.4,1.,(144.,y+1.,-.1))
    a+=root
    from operation_marks import stroke,top_cut
    arrow=stroke([(141.5,y+16),(143.9,y+16)],.45)
    arrow+=stroke([(142.9,y+15),(143.9,y+16),(142.9,y+17)],.45)
    return (a-top_cut(arrow,6.2)).translate((0,0,z))


def modify(p,fixed,leaves):
    # New post/capture locations avoid both the DIMM hoods and release paddles
    # throughout the original eight-millimetre slide.
    new_reliefs=m.Manifold()
    for y,length in CAPTURES:
        new_reliefs+=pair(v.box((6.55,length+.6,7.),(0,y-.3,-.1)))
    for name in ('tray-middle-3','tray-top-3'):
        fixed[name]-=new_reliefs
        # Tongue travel channels occupy only the outer end bars; stay outside
        # component envelopes. Top and middle use the same interchangeable form.
        for y,length in CAPTURES:
            fixed[name]-=pair(v.box((6.4,length+8.6,2.5),(1.8,y-8.3,4.5)))
        leaves[name]=[(y,clip(y,0)) for y,s in leaves[name]]
        p[name]=fixed[name]
        for _,s in leaves[name]:p[name]+=s
    for name in ('body-pin-clearance','body-thread-pilot'):
        a=fixed[name]
        # Low triangular belt braces the long walls in the unused side bays.
        # Its top remains 0.4 mm below the first removable tray, and holes stay open.
        from floor_fillet import mount_voids
        belt=m.CrossSection([[(1.59,7.79),(4.2,10.4),(1.59,10.4)]]).extrude(143.8)
        belt=belt.transform([[0,0,1,1.6],[1,0,0,0],[0,1,0,0]])
        belt+=belt.mirror((0,1,0)).translate((0,101.6,0))
        a+=belt-mount_voids(name.endswith('clearance'))
        # Remove old sloped lips; preserve underlying screw posts.
        a-=pair(v.box((3.3,101.6,1.61),(0,0,24.39)))
        for y,length in CAPTURES:
            # Rigid base, a 0.3 mm vertical tongue gap, and a 2 mm upper flange.
            a+=pair(v.box((6.4,length,22.1),(0,y,0)))
            a-=pair(v.box((6.6,length+8.6,2.6),(1.8,y-8.3,22.1)))
            a+=pair(v.box((2.4,length,3.9),(0,y,22.1)))
            a+=pair(v.box((6.4,length,2.),(0,y,24.)))
            root=v.box((.81,length,.81),(2.39,y,23.19))
            root-=v.cyl(length+.2,.8,(3.2,y-.1,23.2),rot=(-90,0,0))
            a+=pair(root)
        leaves[name]=[(y,clip(y,4.)) for y,s in leaves[name]]
        # Restore optional screw pilots after adding the new posts. At the
        # front capture, a clearance/countersink passes through its upper flange.
        for x,y in v.OPTIONAL:
            a-=v.cyl(8.7,.8,(x,y,16.))
        a-=v.cyl(2.1,1.1,(141.6,10.,23.9))+v.countersink(141.6,10.,26.,4.)
        fixed[name]=a
        p[name]=a+shell_leaf()
        for _,s in leaves[name]:p[name]+=s
    lid=p['lid-slide-lift']
    for y,length in CAPTURES:
        # Closed position: flat tongue below the flange; opening has identical
        # press / slide 8 mm / lift sequence. Riser stays before chip X=8.5.
        lid-=pair(v.box((6.6,length+8.6,2.1),(0,y-.3,24.)))
        lid+=pair(v.box((4.6,length-.4,1.4),(3.4,y+.2,22.4)))
        lid+=pair(v.box((1.4,length-.4,3.6),(6.6,y+.2,22.4)))
        fillet=v.box((.41,length-.4,.41),(7.99,y+.2,24.19))
        fillet-=v.cyl(length-.2,.4,(8.4,y+.1,24.2),rot=(-90,0,0))
        lid+=pair(fillet)
        lid-=pair(v.box((6.6,length+.6,4.),(0,y+7.7,22.3)))
    for x,y in v.OPTIONAL:
        lid-=v.cyl(4.,1.1,(x,y,22.2))+v.countersink(x,y,26.,4.)
    p['lid-slide-lift']=lid
    p={name:s.set_tolerance(.001) for name,s in p.items()}
    return p,fixed,leaves


def configure():
    previous.configure()
    base.VERSION=VERSION
    base.SHELL_LEAF=shell_leaf
    base.PART_MODIFIER=modify


def build(out):
    configure()
    base.build(out)
    p,_,_=base.parts()
    bearing=m.Manifold()
    for y,length in CAPTURES:
        bearing+=pair(v.box((3.,length-.4,3.),(3.4,y+.2,22.)))
    area=(p['body-pin-clearance'].slice(24.01)^p['lid-slide-lift'].slice(23.79)^bearing.slice(24.)).area()
    assert area>50.,area
    for x,y in v.OPTIONAL:
        screw=v.cyl(8.,1.,(x,y,18.))+v.countersink(x,y,26.,4.)
        for name,z in [('lid-slide-lift',0),('tray-middle-3',10.8),('tray-top-3',17.6)]:
            base.clear(screw,p[name].translate((0,0,z)),('optional screw',name,x,y))
    previous.configure()
    old,_,_=base.parts()
    changes={name:{'added_mm3':(s-old[name]).volume(),'removed_mm3':(old[name]-s).volume()} for name,s in p.items()}
    configure()
    report={'version':VERSION,'baseline':'4.0-rc4','matched_complete_set_required':True,
        'changes':changes,'flat_vertical_bearing_area_mm2':area,
        'lid_release_beam_thickness_mm':[1.,1.2],'lid_release_root_radius_mm':1.,
        'lid_lock_tooth_width_mm':[5.,7.],'capture_flange_thickness_mm':2.,
        'capture_tongue_thickness_mm':1.4,'capture_root_radius_mm':.8,
        'lid_riser_root_radius_mm':.4,'pcb_beam_thickness_mm':[.8,1.],
        'pcb_root_radius_mm':1.,'pcb_tooth_width_mm':[4.,4.8],
        'long_wall_belt_top_z_mm':10.4,'tray_entry_gap_above_belt_mm':.4,
        'screw_clearance_checks':6,'physical_impact_verified':False,'physical_cycles_verified':False,
        'limits':'Bearing area and geometric motion checks do not predict load capacity, deflection, printed root strength, fatigue or impact damage.'}
    (out/'reinforcement.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.1-rc1')
    build(parser.parse_args().output_dir.resolve())
