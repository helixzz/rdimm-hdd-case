"""Nominal bead/material audit and production feature-time triage."""
import json
import numpy as np
import evaluate_dfm_geometry as g
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint

def audit(folder):
    segs,_=parse_materials(folder/'plate_1.gcode')
    caps=[p for p in json.loads((folder/'verification.json').read_text())['volumes'] if p['role']=='interface']
    rows=[]
    for cap in caps:
        lo,hi=np.array(cap['bounds']);rect=[lo[0]+.15,lo[1]+.15,hi[0]-.15,hi[1]-.15]
        xx,yy=grid(rect);local=select(segs,rect)
        inside=local[(local[:,8]==1)&(local[:,4]>lo[2]+.001)&(local[:,4]<=hi[2]+.101)]
        layers=np.unique(inside[:,4]);assert len(layers)>=2,(cap['name'],layers)
        ilow=np.full(xx.shape,np.inf);ihigh=np.full(xx.shape,-np.inf)
        bottom=np.full(xx.shape,-np.inf);top=np.full(xx.shape,np.inf)
        for q in inside:
            hit=footprint(q[:8],xx,yy);ilow[hit]=np.minimum(ilow[hit],q[4]-q[6]);ihigh[hit]=np.maximum(ihigh[hit],q[4])
        for q in local[local[:,8]==0]:
            hit=footprint(q[:8],xx,yy)
            if q[4]<(lo[2]+hi[2])/2:bottom[hit]=np.maximum(bottom[hit],q[4])
            elif q[4]-q[6]>(lo[2]+hi[2])/2:top[hit]=np.minimum(top[hit],q[4]-q[6])
        covered=np.isfinite(ilow)&np.isfinite(ihigh)&np.isfinite(bottom)&np.isfinite(top)
        interface_coverage=(np.isfinite(ilow)&np.isfinite(ihigh)).mean()
        lower_contact=float(np.mean(abs(ilow-bottom)<.011));upper_contact=float(np.mean(abs(top-ihigh)<.011))
        assert interface_coverage>.98 and covered.mean()>.8,(cap['name'],interface_coverage,covered.mean())
        assert lower_contact>.8 and upper_contact>.8,(cap['name'],lower_contact,upper_contact)
        assert (ilow[covered]-bottom[covered]).min()>-.011 and (top[covered]-ihigh[covered]).min()>-.011
        rows.append(dict(name=cap['name'],layers=layers.tolist(),interface_coverage=float(interface_coverage),contact=[lower_contact,upper_contact]))
    for q in segs[(segs[:,8]==1)&(segs[:,7]==0)]:
        point=np.array([(q[0]+q[2])/2,(q[1]+q[3])/2,q[4]-q[6]/2])
        assert any(np.all(point>=np.array(c['bounds'][0])-.11) and np.all(point<=np.array(c['bounds'][1])+.11) for c in caps)
    for rect,lo,hi in [([158.4,116.575,161.6,119.775],0,5.31),([148.1,115,151.9,120.7],4.4,8.3)]:
        s=select(segs,rect);assert not len(s[(s[:,7]==1)&(s[:,4]>lo)&(s[:,4]-s[:,6]<hi)])
    return dict(interfaces=rows,unexpected_support_material_model_paths=0,h32_hole_support_paths=0)

def residue_study():
    """Controlled local residue blocks; not a prediction of real roughness."""
    rows=[]
    g.design.configure();old,f,l=g.base.parts()
    new,_,_=g.full_geometry(relief=True)
    for name,count,z in [('body-pin-clearance',2,4.),('tray-middle-3',3,0.),('tray-top-3',3,0.)]:
        for i,sy in enumerate(g.v.layout(count)[2]):
            ty=l[name][i][0]-(2.8 if count==3 and i==0 else 0)
            ram=g.base.rc.simple.module(133.8,31.4,1.37,6.6,sy+.2).translate((0,0,z))
            for side,x,dx,cy,dy in [('fixed',6.7,1.,sy+13.4,5.2),('spring',139.6,.7,ty+15,2.)]:
                for h in (.1,.2,.3,.4):
                    # Pocket floor is 2.69; new roughness must stay below seat Z3.
                    before=g.v.box((dx,dy,h),(x,cy,z+3))
                    after=g.v.box((dx,dy,h),(x,cy,z+2.69))
                    a=(before^ram).volume();b=(after^ram).volume()
                    assert a>0 and (b<1e-7 if h<=.3 else b>0),(name,i,side,h,a,b)
                    rows.append(dict(part=name,slot=i+1,side=side,residue_mm=h,old_collision_mm3=a,new_collision_mm3=b))
            # Positive control: residue on a retained bearing land is NOT cured.
            land=g.v.box((1.,.4,.2),(6.7,sy+12.4,z+3))
            assert (land^ram).volume()>0
    return dict(rows=rows,retained_land_residue_still_interferes=True,
                scope='Uniform blocks only inside proposed pockets, nominal seated PCB; does not predict actual residue shapes or location.')

def grip_layer_overlap():
    segs,_=parse_materials(g.OUT/'combined/plate_1.gcode');rows=[]
    for i,core in enumerate(g.specimens('combined')[0]['cores']):
        lo,hi=np.array(core.bounding_box()).reshape(2,3)+[45,45,0]
        xx,yy=np.meshgrid(np.arange(lo[0]-.25,hi[0]+.25,.05),np.arange(lo[1]-.25,hi[1]+.25,.05))
        local=select(segs,[lo[0]-.3,lo[1]-.3,hi[0]+.3,hi[1]+.3]);layers=[]
        for z in np.arange(3.6,6.601,.2):
            current=np.zeros(xx.shape,bool);previous=current.copy()
            for q in local[np.abs(local[:,4]-z)<.01]:
                if q[8]==0:current|=footprint(q[:8],xx,yy)
            for q in local[np.abs(local[:,4]-(z-.2))<.01]:previous|=footprint(q[:8],xx,yy)
            if not current.any():continue
            fraction=float((current&previous).sum()/current.sum())
            assert fraction>.5,(i,z,fraction)
            layers.append(dict(z_mm=round(float(z),2),previous_layer_overlap_fraction=fraction))
        rows.append(dict(core=i+1,layers=layers))
    return dict(rows=rows,grid_mm=.05,scope='Aggregate PLA footprint overlap within each grip bounding box, includes nearby keep geometry; not a local overhang or strength guarantee.')

def main():
    report={}
    for name in ('paddle','raised-grips','combined'):
        report[name]=audit(g.OUT/name);print('Audited',name,len(report[name]['interfaces']),flush=True)
    report['residue']=residue_study()
    report['raised_grip_layer_overlap']=grip_layer_overlap()
    rows=[]
    for name in ('1-pin-clearance','2-upper-trays'):
        folder=g.ROOT/f'build/v4.3-projects/{name}'
        p=json.loads((folder/'result.json').read_text())['sliced_plates'][0]
        rows.append(dict(plate=name,seconds=p['total_predication'],feature_seconds=p['feature_type_times']))
        segs,features=parse_materials(folder/'plate_1.gcode')
        bridges=segs[np.array(features)=='Bridge']
        lengths=np.hypot(bridges[:,2]-bridges[:,0],bridges[:,3]-bridges[:,1])
        distribution={str(float(z)):float(lengths[bridges[:,4]==z].sum()) for z in np.unique(bridges[:,4])}
        (g.OUT/(name+'-bridge-distribution.json')).write_text(json.dumps(dict(plate=name,bridge_path_length_mm_by_layer_z=distribution),indent=2))
    report['production_baseline']=rows
    report['limits']='Nominal beads and controlled geometric obstructions, no adhesion/strength/thermal or force simulation.'
    (g.OUT/'audit.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
