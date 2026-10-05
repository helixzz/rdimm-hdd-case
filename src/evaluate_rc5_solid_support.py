"""Post-RC5 research: solid dedicated supports and handles, no mixed keys.

Research only. Successful slicing does not validate adhesion or surface finish.
Uses local resolved RC4 printer/filament settings, never exports vendor presets.
"""
import argparse,json
import study_sparse_peel_v4_4 as s

original_dimm=s.dimm_insert
original_capture=s.capture_insert

def dimm(moving,gap,keyed=False):
    assert not keyed
    solid,rec,handle=original_dimm(moving,gap,False)
    x0,x1=rec['contact_x_mm'];a=rec['ribs'][0][0];b=sum(rec['ribs'][-1])
    solid+=s.v.box((x1-x0,b-a,1.6),(x0,a,3.))
    rec.update(ribs=[(a,b-a)],rib_count=1,max_clear_gap_mm=0.,contact_fraction=1.)
    return solid.set_tolerance(.001).simplify(.001),rec,handle

def capture(length,gap,keyed=False):
    assert not keyed
    solid,rec,handle=original_capture(length,gap,False)
    a=rec['ribs'][0][0];b=sum(rec['ribs'][-1])
    solid+=s.v.box((2.9,b-a,1.9),(3.4,a,2.9))
    rec.update(ribs=[(a,b-a)],rib_count=1,max_clear_gap_mm=0.,contact_fraction=1.)
    return solid.set_tolerance(.001).simplify(.001),rec,handle

def main(bambu=None):
    old=s.dimm_insert,s.capture_insert
    try:
        s.dimm_insert=dimm;s.capture_insert=capture
        qs=s.coupons(.8,False);report={'coupon_geometry':s.verify(qs)}
        plates,checks=s.product(.8,False);report['complete_geometry']=checks;report['plates']=[]
        out=s.ROOT/'build/rc5-solid-support-study';out.mkdir(parents=True,exist_ok=True)
        for label,items in plates:
            folder=out/label;folder.mkdir(exist_ok=True)
            source=s.full.export(items,folder,'SOLID-SUPPORT-'+label)
            if bambu:report['plates'].append(dict(plate=label,**s.slice_project(source,folder,bambu)))
        report.update(physical_verified=False,release=False,
            limits='All removable pads and extensions use Support For PLA; product unchanged. Contacts enlarged. Geometry/extraction/slicing only; adhesion, first-layer stability, quality and breakaway force unverified.')
        (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    finally:s.dimm_insert,s.capture_insert=old

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu');a=p.parse_args();main(a.bambu)
