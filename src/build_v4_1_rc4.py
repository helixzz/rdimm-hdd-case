"""RC4 replacement lid: continuous neck clearance with a sloped root transition."""
import argparse
import json
import zipfile
from pathlib import Path
import numpy as np
import build_v4_1_rc3 as previous

base=previous.base
v=previous.v
m=previous.m
VERSION='4.1-rc4'


def modify(p,fixed,leaves):
    p,fixed,leaves=previous.previous.modify(p,fixed,leaves)
    lid=p['lid-slide-lift'];pair=previous.previous.previous.pair
    for y,length in previous.previous.previous.CAPTURES:
        start=y+.2;end=y+length-.2
        # Continue X=6.8 clearance to Z=23.7, returning to X=6.6 at
        # Z=23.4. The flange bearing footprint ends at X=6.4.
        lid-=pair(v.box((.2,length+8.6,2.31),(6.6,y-.3,23.7)))
        relief=m.CrossSection([[(6.599,23.399),(6.8,23.7),
                                (6.8,23.701),(6.599,23.701)]])
        relief=relief.extrude(length+8.6).rotate((90,0,0)).translate((0,y+length+8.3,0))
        lid-=pair(relief)
        # Retain RC3 tongue and its end chamfers. Extend the ramp cutter
        # 0.00001 mm beyond the coplanar top to avoid zero-thickness debris.
        lid-=pair(v.box((3.01,length-.4,.201),(3.39,start,23.6)))
        ramp=m.CrossSection([[(6.39,23.595),(6.8,23.8),(6.8,23.80001),(6.39,23.80001)]]).extrude(length-.38).rotate((90,0,0)).translate((0,end+.01,0))
        lid-=pair(ramp)
        lid-=pair(previous.yz_prism([(end-.6,23.6),(end+.01,23.6),(end+.01,23.295)],x1=6.4))
        lid-=pair(previous.yz_prism([(end-.6,22.4),(end+.01,22.4),(end+.01,22.705)]))
        lid-=pair(previous.yz_prism([(start-.01,23.6),(start+.3,23.6),(start-.01,23.393)],x1=6.4))
        lid-=pair(previous.yz_prism([(start-.01,22.4),(start+.3,22.4),(start-.01,22.607)]))
    p['lid-slide-lift']=lid.set_tolerance(.001)
    return p,fixed,leaves


def configure():
    previous.configure()
    base.VERSION=VERSION
    base.PART_MODIFIER=modify


def build(out):
    configure();base.build(out,lid_up_probe=.55)
    new,_,_=base.parts()
    previous.configure();old,_,_=base.parts()
    previous.previous.configure();rc2,fixed,_=base.parts()
    changes={}
    for name,s in new.items():
        added=(s-old[name]).volume();removed=(old[name]-s).volume()
        assert added<.001,(name,added)
        if name!='lid-slide-lift':assert removed<.001,(name,removed)
        changes[name]={'added_mm3':added,'removed_mm3':removed}
    lid=new['lid-slide-lift'];body=fixed['body-pin-clearance']
    base.clear(lid,rc2['body-pin-clearance'],'RC4 lid / complete RC2 body')
    # Combined rigid poses reproduce the missed RC3 shoulder contact.
    # Exclude elastic latches: their release is covered by the full path audit.
    checks=[]
    for dx in (-.3,0.,.3):
        for dz in (0.,.15,.25):
            for dy in np.linspace(-8.,0.,33):
                vol=(lid.translate((dx,float(dy),dz))^body).volume()
                assert vol<.001,('combined capture clearance',dx,dy,dz,vol)
                checks.append({'offset_mm':[dx,float(dy),dz],'intersection_mm3':vol})
    old_failure=(old['lid-slide-lift'].translate((.3,0,.15))^body).volume()
    assert old_failure>.1,old_failure
    # An exploratory downward+sideways probe reaches the shell rim, not the
    # relieved neck. Preserve and disclose it rather than claiming universal
    # offset clearance: the actual nominal path remains checked by base.verify.
    rim_probe={}
    for label,shape in [('rc3',old['lid-slide-lift']),('rc4',lid)]:
        hit=shape.translate((-.3,-8.,-.15))^body
        rim_probe[label]={'intersection_mm3':hit.volume(),'bounds_mm':list(hit.bounding_box())}
    assert abs(rim_probe['rc3']['intersection_mm3']-rim_probe['rc4']['intersection_mm3'])<.001
    bearing=m.Manifold()
    for y,length in previous.previous.previous.CAPTURES:
        bearing+=previous.previous.previous.pair(v.box((3.,length-.4,3.),(3.4,y+.2,22.)))
    base.clear(old['lid-slide-lift']-lid,bearing,'unchanged RC3 bearing region')
    area=(body.slice(24.01)^lid.slice(23.599)^bearing.slice(24.)).area()
    old_area=(body.slice(24.01)^old['lid-slide-lift'].slice(23.599)^bearing.slice(24.)).area()
    assert abs(area-old_area)<.001 and area>40.,(area,old_area)
    for x,y in v.OPTIONAL:
        base.clear(v.cyl(4.,1.,(x,y,22.))+v.countersink(x,y,26.,4.),lid,'optional lid screw')
    report=json.loads((out/'verification.json').read_text(encoding='utf8'))
    pose=next(q for r in report['plate_records'] if r['stem'].endswith('plate-1-pin-clearance') for q in r['poses'] if q['part']=='lid-slide-lift')
    mesh=v.meshof(lid);mesh.apply_transform(np.array(pose['assembly_to_plate']))
    stem=f'rdimm-{VERSION}-plate-3-replacement-lid'
    mesh.export(out/(stem+'.stl'));base.rc.export_geometry(out/(stem+'.3mf'),mesh)
    path=out/(stem+'.3mf')
    with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
    data['3D/3dmodel.model']=data['3D/3dmodel.model'].replace(b'case v3.1',('case v'+VERSION).encode())
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,value in data.items():z.writestr(name,value)
    report['plate_records'].append({'stem':stem,'poses':[pose],'bounds':mesh.bounds.tolist()})
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (out/'lid-fit.json').write_text(json.dumps({'version':VERSION,'baseline':'4.1-rc3','changes':changes,
        'compatible_existing_body_and_trays':['4.1-rc1','4.1-rc2'],
        'main_tongue_thickness_mm':1.2,'root_thickness_mm':1.4,'upper_riser_min_width_mm':1.2,
        'continuous_side_gap_mm':.4,'side_relief_bottom_z_mm':23.7,'root_transition_z_mm':[23.4,23.7],
        'main_vertical_clearance_above_mm':.4,'main_vertical_clearance_below_mm':.3,
        'leading_ramp_length_mm':.6,'flat_bearing_area_mm2':area,'rc3_bearing_area_mm2':old_area,
        'closed_lid_upward_stop_probe_mm':.55,'rc3_combined_pose_intersection_mm3':old_failure,
        'combined_pose_checks':checks,'offsets_are_measured':False,
        'unchanged_sideways_downward_rim_contact':{'offset_mm':[-.3,-8.,-.15],
            'scope':'Separate shell-rim contact outside the neck; not fixed in this neck-only revision.',**rim_probe},
        'physical_fit_verified':False,'physical_strength_verified':False,
        'limits':'Rigid clearance probes do not model warp, surface roughness, force, fatigue or impact. Local neck material removed; unchanged bearing area does not establish unchanged strength.'},indent=2),encoding='utf8')
    configure()
    print('RC4 replacement lid:',len(checks),'combined poses; bearing area',area,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.1-rc4')
    build(parser.parse_args().output_dir.resolve())
