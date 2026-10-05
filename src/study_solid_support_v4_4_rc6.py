"""Solid dedicated supports with broad, lower grips; complete-product screening.

No sparse fingers, separate films or mixed-material mechanical keys. Nominal
geometry/paths do not simulate support adhesion or nozzle-induced displacement.
"""
import argparse,json
from contextlib import contextmanager
import study_sparse_peel_v4_4 as s

ROOT=s.ROOT;v=s.v;base=s.base;full=s.full

def dimm(moving,gap,keyed=False,height=5.4):
    assert not keyed and height>=4.8
    a,b=(28.35,32.65) if moving else (14.85,22.05)
    x=6.95 if moving else 6.65
    solid=v.box((7.9-x,b-a,1.6),(x,a,3.))
    tip=7.75+(height-1.-3.)
    solid+=base.rc.wedge([(7.75,3.),(tip,height-1.),(tip,height),(8.05,height),(8.05,4.6),(7.75,4.6)],a,b-a)
    if moving:solid=solid.mirror((1,0,0)).translate((147.3,0,0))
    return solid.set_tolerance(.001).simplify(.001),dict(kind='moving' if moving else 'fixed',
        ribs=[(a,b-a)],rib_count=1,max_clear_gap_mm=0.,contact_fraction=1.,
        contact_x_mm=[139.4,140.35] if moving else [6.65,7.9],contact_z_mm=[3.,4.6],
        grip_height_mm=height,grip_tip_thickness_mm=1.,grip_projection_mm=tip-7.9),v.m.Manifold()

def capture(length,gap,keyed=False,height=5.4):
    assert not keyed and height>=4.8
    a,b=2.3,2+length-.3
    solid=v.box((2.9,b-a,1.9),(3.4,a,2.9))
    tip=6.15+(height-1.-2.9)
    solid+=base.rc.wedge([(6.15,2.9),(tip,height-1.),(tip,height),(6.55,height),(6.55,4.8),(6.15,4.8)],a,b-a)
    return solid.set_tolerance(.001).simplify(.001),dict(kind='capture',ribs=[(a,b-a)],rib_count=1,
        max_clear_gap_mm=0.,contact_fraction=1.,contact_x_mm=[3.4,6.3],contact_z_mm=[2.9,4.8],
        grip_height_mm=height,grip_tip_thickness_mm=1.,grip_projection_mm=tip-6.3),v.m.Manifold()

@contextmanager
def variant(height):
    old=s.dimm_insert,s.capture_insert
    s.dimm_insert=lambda m,g,k=False:dimm(m,g,k,height)
    s.capture_insert=lambda l,g,k=False:capture(l,g,k,height)
    try:yield
    finally:s.dimm_insert,s.capture_insert=old

def coupons(height=5.4):
    with variant(height):return s.coupons(.8,False)

def product(height=5.4,bare=False):
    with variant(height):plates,checks=s.product(.8,False)
    if bare:
        for _,items in plates:
            for q in items:q['interfaces']=[]
        for row in checks['details']:row.update(cores=0,interfaces=0,core_extraction_poses=0)
        checks.update(connected_insert_count=0,insert_extraction_poses=0)
        checks['scope']='No modeled local supports; diagnostic control, not qualified'
    return plates,checks

def main(bambu,heights,bare=False):
    out=ROOT/'build/rc6-solid-study';out.mkdir(parents=True,exist_ok=True)
    for h in heights:
        name='no-local-support' if bare else f'grip-{h:.1f}'
        plates,checks=product(h,bare);report=dict(geometry=checks,plates=[],physical_verified=False)
        if not bare:report['coupons']=s.verify(coupons(h))
        for label,items in plates:
            folder=out/name/label;folder.mkdir(parents=True,exist_ok=True)
            original=full.export(items,folder,'RC6-STUDY-'+name+'-'+label)
            if bambu:report['plates'].append(dict(plate=label,**s.slice_project(original,folder,bambu)))
        (out/(name+'.json')).write_text(json.dumps(report,indent=2));print(name,json.dumps(report),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--bambu');ap.add_argument('--heights',nargs='+',type=float,default=[5.,5.4]);ap.add_argument('--bare',action='store_true');a=ap.parse_args();main(a.bambu,a.heights,a.bare)
