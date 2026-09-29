"""RC3 replacement lid: lead-in chamfers and more lateral capture clearance."""
import argparse
import json
import zipfile
from pathlib import Path
import numpy as np
import build_v4_1_rc2 as previous

base=previous.base
v=previous.v
m=previous.m
VERSION='4.1-rc3'


def yz_prism(points,x0=3.39,x1=8.01):
    if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1]))<0:points=list(reversed(points))
    return m.CrossSection([points]).extrude(x1-x0).transform([[0,0,1,x0],[1,0,0,0],[0,1,0,0]])


def modify(p,fixed,leaves):
    p,fixed,leaves=previous.modify(p,fixed,leaves)
    lid=p['lid-slide-lift'];pair=previous.previous.pair
    for y,length in previous.previous.CAPTURES:
        start=y+.2;end=y+length-.2
        # Preserve the 1.4 mm root. Relieve only the upper
        # riser/notch beside the 6.4 mm body flange: 0.2 -> 0.4 mm side gap.
        lid-=pair(v.box((.2,length+8.6,2.01),(6.6,y-.3,24.)))
        # Full travel vertical relief on the support-facing bearing surface:
        # tongue 1.4 -> 1.2 mm; upper gap 0.2 -> 0.4 mm. Blend into full root
        # beyond the body flange, preserving the component-side envelope.
        lid-=pair(v.box((3.01,length-.4,.201),(3.39,start,23.6)))
        ramp=m.CrossSection([[(6.39,23.595),(6.8,23.8),(6.39,23.8)]]).extrude(length-.38).rotate((90,0,0)).translate((0,end+.01,0))
        lid-=pair(ramp)
        # Closing travels +Y. Taper both edges at its leading end from 1.2
        # to 0.6 mm, over 0.6 mm; main tongue remains full thickness.
        lid-=pair(yz_prism([(end-.6,23.6),(end+.01,23.6),(end+.01,23.295)],x1=6.4))
        lid-=pair(yz_prism([(end-.6,22.4),(end+.01,22.4),(end+.01,22.705)]))
        # Smaller exit chamfers help release without thinning the whole foot.
        lid-=pair(yz_prism([(start-.01,23.6),(start+.3,23.6),(start-.01,23.393)],x1=6.4))
        lid-=pair(yz_prism([(start-.01,22.4),(start+.3,22.4),(start-.01,22.607)]))
    p['lid-slide-lift']=lid.set_tolerance(.001)
    return p,fixed,leaves


def configure():
    previous.configure();base.VERSION=VERSION;base.PART_MODIFIER=modify


def build(out):
    configure();base.build(out,lid_up_probe=.55)
    p,_,_=base.parts()
    previous.configure();old,_,_=base.parts()
    changes={}
    for name,s in p.items():
        add=(s-old[name]).volume();remove=(old[name]-s).volume()
        assert add<.001,(name,add)
        if name!='lid-slide-lift':assert remove<.001,(name,remove)
        changes[name]={'added_mm3':add,'removed_mm3':remove}
    # New lid against the actual previous version's complete assembly.
    base.clear(p['lid-slide-lift'],old['body-pin-clearance'],'RC2 body / RC3 lid')
    perturbations=[]
    for dx in (-.3,.3):
        old_overlap=(old['lid-slide-lift'].translate((dx,0,0))^old['body-pin-clearance']).volume()
        new_overlap=(p['lid-slide-lift'].translate((dx,0,0))^old['body-pin-clearance']).volume()
        assert old_overlap>.1 and new_overlap<.001,(dx,old_overlap,new_overlap)
        perturbations.append({'lateral_shift_mm':dx,'old_body_overlap_mm3':old_overlap,'new_body_overlap_mm3':new_overlap})
    bearing=m.Manifold()
    for y,length in previous.previous.CAPTURES:
        bearing+=previous.previous.pair(v.box((3.,length-.4,3.),(3.4,y+.2,22.)))
    area=(old['body-pin-clearance'].slice(24.01)^p['lid-slide-lift'].slice(23.599)^bearing.slice(24.)).area()
    assert area>40.,area
    for x,y in v.OPTIONAL:
        base.clear(v.cyl(4.,1.,(x,y,22.))+v.countersink(x,y,26.,4.),p['lid-slide-lift'],'optional lid screw')
    # Existing RC2 plate pose keeps the lid upside down with its outside on bed.
    report=json.loads((out/'verification.json').read_text(encoding='utf8'))
    pose=next(q for r in report['plate_records'] if r['stem'].endswith('plate-1-pin-clearance') for q in r['poses'] if q['part']=='lid-slide-lift')
    mesh=v.meshof(p['lid-slide-lift']);mesh.apply_transform(np.array(pose['assembly_to_plate']))
    stem=f'rdimm-{VERSION}-plate-3-replacement-lid'
    mesh.export(out/(stem+'.stl'));base.rc.export_geometry(out/(stem+'.3mf'),mesh)
    path=out/(stem+'.3mf')
    with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
    data['3D/3dmodel.model']=data['3D/3dmodel.model'].replace(b'case v3.1',('case v'+VERSION).encode())
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,value in data.items():z.writestr(name,value)
    report['plate_records'].append({'stem':stem,'poses':[pose],'bounds':mesh.bounds.tolist()})
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (out/'lid-fit.json').write_text(json.dumps({'version':VERSION,'baseline':'4.1-rc2','changes':changes,
        'compatible_existing_body_and_trays':['4.1-rc1','4.1-rc2'],
        'main_tongue_thickness_mm':1.2,'root_thickness_mm':1.4,'upper_riser_min_width_mm':1.2,
        'flange_to_riser_gap_mm':[.2,.4],'main_vertical_clearance_above_mm':.4,
        'main_vertical_clearance_below_mm':.3,'leading_ramp_length_mm':.6,
        'leading_edge_thickness_mm':.6,'flat_bearing_area_mm2':area,
        'closed_lid_upward_stop_probe_mm':.55,'lateral_perturbation_checks':perturbations,
        'physical_fit_verified':False,'physical_strength_verified':False,
        'limits':'Fit candidate for reported entry and full-travel jamming. Material removal reduces some sections; no claim of unchanged strength, proven printed fit or operating force.'},indent=2),encoding='utf8')
    configure()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.1-rc3')
    build(parser.parse_args().output_dir.resolve())
