"""A separately printed fixed-end keeper with keyhole mounts and a stop latch.

One keeper per complete tray/base. Inverted print orientation avoids the old
horizontal DIMM slot support. No assertion of physical force or fatigue.
"""
import json
import numpy as np
import study_sparse_peel_v4_4 as study
v=study.v;base=study.base;ROOT=study.ROOT

def slot(c1,c2,r,z,height):
    return (v.cyl(height,r,(5.2,c1,z))+v.cyl(height,r,(5.2,c2,z))+
            v.box((2*r,abs(c2-c1),height),(5.2-r,min(c1,c2),z)))

def tapered_slot(c1,c2):
    # In the inverted print orientation the hole narrows .15 mm per .2 layer;
    # there is no flat unsupported internal roof to fill with auto-support.
    ends=v.cyl(1.2,1.1,(5.2,c1,5.2),r2=2.)+v.cyl(1.2,1.1,(5.2,c2,5.2),r2=2.)
    return ends+base.rc.wedge([(4.1,5.2),(6.3,5.2),(7.2,6.4),(3.2,6.4)],min(c1,c2),abs(c2-c1))

def split(keep,ys,end=None):
    start=ys[0]+12.2;end=end or ys[-1]+20.5
    # Flat seating surfaces and two positive mushroom mounts; remove only the
    # fixed-end rail/hoods, preserving PCB seat Z3 and moving clip geometry.
    cut=v.box((6.03,end-start+3.81,2.5),(1.89,start,4.4))
    # First hood's leading .2 mm is removed too; restored on the new keeper.
    for sy in ys:cut+=v.box((6.03,8.002,2.5),(1.89,sy+11.999,4.4))
    body=keep-cut
    rail=v.box((6.,end-start,2.2),(1.9,start,4.6))
    # Remove the overhang except at the original retention lands. This makes
    # the upper keeper a rail plus short teeth, rather than a full-length roof.
    rail-=v.box((1.61,end-start,.91),(6.29,start,4.59))
    for sy in ys:
        rail+=v.box((1.6,8.,2.2),(6.3,sy+12,4.6))
    y1=start+10.;y2=end-(15. if end-start>40 else 5.)
    assert y2-y1>=7
    for y in (y1,y2):
        stud=v.cyl(1.,.9,(5.2,y,4.4))+v.cyl(.8,.9,(5.2,y,5.4),r2=1.7)
        body+=stud
        # Installed position at y; large entry lies 3.8 mm toward -Y.
        rail-=v.cyl(3.,2.,(5.2,y-3.8,4.3))
        rail-=slot(y-3.8,y,1.1,4.3,2.6)
        rail-=tapered_slot(y-3.8,y)
    # Open-sided, accessible latch; it only blocks reverse sliding. Studs
    # carry upward loads. Flexure remains attached to the rail at its root.
    root=end-11.;tip=end-1.0
    rail-=v.box((1.51,11.1,2.6),(1.89,root,4.3))
    beam=v.box((1.1,10.1,1.0),(1.9,root-.1,5.8))
    tooth=v.box((1.1,.7,1.5),(1.9,tip-.7,4.3))
    leaf=beam+tooth
    rail+=leaf
    floor=2.4 if keep.bounding_box()[2]<-.1 else 0.
    body+=v.box((1.5,3.,4.4-floor),(1.9,tip-1.5,floor))
    if floor==0:body+=v.box((6.61,3.02,.61),(1.9,tip-1.51,0))
    body-=v.box((1.5,1.2,.7),(1.7,tip-.95,3.9))
    # Source relief edge is float32 X6.55; Boolean floor unions can leave
    # collinear sub-micron slivers there. Snap only that analytic datum.
    body=body.warp(lambda p:(6.55 if abs(p[0]-6.55)<.001 else p[0],p[1],p[2]))
    body=body.set_tolerance(.001).simplify(.001);rail=rail.set_tolerance(.001).simplify(.001)
    leaf=leaf.set_tolerance(.001).simplify(.001)
    return body,rail,leaf,dict(start=start,end=end,stud_y=[y1,y2],latch_root=root,latch_tip=tip,slide_mm=3.8)

def lift_leaf(leaf,root,travel=.5):
    return leaf.warp(lambda p:(p[0],p[1],p[2]+travel*min(1,max(0,(p[1]-root)/8.5))**2))

def verify(body,rail,leaf,record,label):
    for name,s in [('body',body),('keeper',rail)]:
        assert len(s.decompose())==1,(label,name,'disconnected',len(s.decompose()))
        mesh=v.meshof(s);assert mesh.is_watertight and mesh.is_winding_consistent
    base.clear(body,rail,(label,'assembled'))
    for travel in np.linspace(0,.5,11):
        base.clear(body,lift_leaf(leaf,record['latch_root'],float(travel)),(label,'latch lift',travel))
    fixed=rail-leaf;released=fixed+lift_leaf(leaf,record['latch_root'])
    poses=0
    for dy in np.linspace(0,3.8,39):
        base.clear(body,released.translate((0,float(dy),0)),(label,'released slide',dy));poses+=1
    for dz in np.linspace(0,8,41):
        base.clear(body,released.translate((0,3.8,float(dz))),(label,'entry lift',dz));poses+=1
    for direction in [(0,0,.5),(.5,0,0),(-.5,0,0),(0,-.5,0),(0,.5,0)]:
        assert (body^rail.translate(direction)).volume()>.001,(label,'missing stop',direction)
    return dict(assembly_poses=poses,latch_lift_poses=11,positive_stops=5,physical_verified=False)

def full_geometry():
    p,f,l,_=study.full.geometry(True);records={};pieces={};expected={}
    for name in ('body-pin-clearance','body-thread-pilot','tray-middle-3','tray-top-3'):
        body=name.startswith('body');z=4. if body else 0.;ys=v.layout(2 if body else 3)[2]
        # Operate at local tray height for identical retention faces.
        local=p[name].translate((0,0,-z));b,r,leaf,rec=split(local,ys)
        records[name]=verify(b,r,leaf,rec,name)
        p[name]=(b+r).translate((0,0,z));f[name]=(f[name]-(local-b).translate((0,0,z)))+(b-local).translate((0,0,z))+r.translate((0,0,z))
        # The separate keeper is intentionally a second connected component.
        expected[name]=2;pieces[name]=(b.translate((0,0,z)),r.translate((0,0,z)))
    checks=base.verify(p,f,l,lid_up_probe=.55,mount_probe_radius=1.6,component_counts=expected)
    return pieces,dict(complete_product=checks,keeper_checks=records)

def product():
    pieces,checks=full_geometry();plates,_=study.product(.8,True)
    for label,items in plates:
        additions=[];index=0
        for q in items:
            if q['name'] not in pieces:continue
            b,r=pieces[q['name']];t=np.linalg.inv(q['inverse']);q['model']=b.transform(t[:3,:])
            keep=[i for i,rec in enumerate(q['insert_records']) if rec['kind']!='fixed']
            for key in ('cores','interfaces','insert_records'):q[key]=[q[key][i] for i in keep]
            q['rois']=[(a,c) for a,c in q['rois'] if a[0]>100 or a[2]>20]
            r=r.rotate((180,0,0));lo=np.array(r.bounding_box()[:3]);r=r.translate(-lo+[216+index*12,20,0]);index+=1
            additions.append(dict(name='keeper-'+q['name'],kind='keeper',model=r,cores=[],interfaces=[],translation=[0,0,0],inverse=np.eye(4).tolist(),rois=[]))
        items.extend(additions)
    return plates,checks

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--bambu');args=ap.parse_args()
    q=study.g.specimens('combined')[0];s=q['model']+v.box((4.4,14.,4.4),(1.9,34.9,0))
    b,r,leaf,rec=split(s,[2.5],end=45.)
    print(verify(b,r,leaf,rec,'coupon'),flush=True)
    _,report=full_geometry();out=ROOT/'build/split-keeper-study';out.mkdir(parents=True,exist_ok=True)
    (out/'geometry.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
    if args.bambu:
        plates,report=product();report['plates']=[]
        for label,items in plates:
            folder=out/label;folder.mkdir(parents=True,exist_ok=True)
            original=study.full.export(items,folder,'SPLIT-KEEPER-'+label)
            report['plates'].append(dict(plate=label,**study.slice_project(original,folder,args.bambu)))
        (out/'slicing.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
