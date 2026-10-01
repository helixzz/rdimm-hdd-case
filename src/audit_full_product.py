"""Whole product checks: dedicated interfaces, bores, release corridors and tower."""
import json
import numpy as np
from evaluate_full_product import ROOT,OUT,v,base
from audit_dfm_study import audit
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint

def check(folder):
    manifest=json.loads((folder/'verification.json').read_text());has_caps=any(x['role']=='interface' for x in manifest['volumes'])
    report=audit(folder,False,False,'RESEARCH-not-released.3mf') if has_caps else {}
    paths,features=parse_materials(folder/'plate_1.gcode',excluded_features=('Custom','Flush'));features=np.array(features)
    bead_dimensions={key:dict(width_min_max_mm=[float(paths[features==key,5].min()),float(paths[features==key,5].max())],
                             height_mm=np.unique(paths[features==key,6]).tolist())
                     for key in ('Outer wall','Top surface','Sparse infill','Internal solid infill') if np.any(features==key)}
    boundslo=np.minimum(paths[:,:2],paths[:,2:4])-paths[:,5:6]/2
    boundshi=np.maximum(paths[:,:2],paths[:,2:4])+paths[:,5:6]/2
    assert boundslo.min()>=0 and boundshi.max()<=256,(folder,boundslo.min(),boundshi.max())
    tower=paths[features=='Prime tower'];tower_bounds=None;min_tower_gap=None
    if len(tower):
        lo=(np.minimum(tower[:,:2],tower[:,2:4])-tower[:,5:6]/2).min(0)
        hi=(np.maximum(tower[:,:2],tower[:,2:4])+tower[:,5:6]/2).max(0);tower_bounds=[lo.tolist(),hi.tolist()]
        gaps=[]
        for part in manifest['volumes']:
            a,b=np.array(part['bounds'])[:,:2]
            gap=np.maximum(0,np.maximum(a-hi,lo-b));assert np.any(gap>0),('tower bounding overlap',folder,part['name'])
            gaps.append(float(np.linalg.norm(gap)))
        min_tower_gap=min(gaps)
    # Ignore the prime tower when checking local functional corridors.
    paths=paths[features!='Prime tower'];bores=[];corridors=[];paddles=[]
    for part in manifest['specimens']:
        name=part['name']
        if name.startswith('lid'):continue
        t=np.array(part['inverse']);local=paths.copy()
        for cols in ((0,1),(2,3)):
            xyz=np.c_[paths[:,cols[0]],paths[:,cols[1]],paths[:,4]]@t[:3,:3].T+t[:3,3]
            local[:,cols[0]]=xyz[:,0];local[:,cols[1]]=xyz[:,1];local[:,4]=xyz[:,2]
        body=name.startswith('body');n=2 if body else 3;z=4. if body else 0.
        if body:
            for x in v.SIDE_X:
                for ya,yb in ((0.,5.7),(v.W-5.7,v.W)):
                    q=select(local,[x-1.5,ya,x+1.5,yb]);q=q[(q[:,7]==1)&(q[:,4]>4.85)&(q[:,4]-q[:,6]<7.85)]
                    assert not len(q),('side hole support',name,x,ya);bores.append([name,'side',x,ya])
            for x in v.BOTTOM_X:
                for y in v.BOTTOM_Y:
                    q=select(local,[x-1.4,y-1.4,x+1.4,y+1.4]);q=q[(q[:,7]==1)&(q[:,4]<=5.3)]
                    assert not len(q),('bottom hole support',name,x,y);bores.append([name,'bottom',x,y])
        for i,sy in enumerate(v.layout(n)[2]):
            y=base.rc.simple.clip_start(n,i,sy)
            rootshift=2.8 if n==3 and i==0 else 0.
            rect=[141.35,y+1+rootshift,141.75,y+13];xx,yy=grid(rect)
            q=select(local,rect);q=q[(q[:,4]>z+.2)&(q[:,4]-q[:,6]<z+6.1)]
            hits=sum(bool(footprint(s[:8],xx,yy).any()) for s in q)
            assert not hits,('free clip corridor filled',name,i,hits);corridors.append([name,i+1])
            q=select(local,[143.25,y+13.8,144.1,y+18.2]);q=q[(q[:,7]==1)&(q[:,4]<=z+5.4)&(q[:,4]>z)]
            # Report presence; do not suppress a real unwanted support.
            paddles.append(dict(part=name,clip=i+1,automatic_support_segments=len(q)))
    report.update(mount_holes_without_support=bores,free_clip_corridors=corridors,paddle_support=paddles,
                  print_xy_bounds=[boundslo.min(0).tolist(),boundshi.max(0).tolist()],tower_xy_bounds=tower_bounds,tower_min_model_bbox_gap_mm=min_tower_gap,
                  bead_dimensions=bead_dimensions,
                  limits='Nominal toolpaths only, tower clearance is planar bounding-box clearance, not a nozzle/gantry simulation; no adhesion or thermal warpage proof.')
    (folder/'whole-plate-audit.json').write_text(json.dumps(report,indent=2));return report

def main():
    rows=[]
    for mode in ('dual-selective','axis-aligned','wider-internal','combined-infill','wide-combined'):
        for plate in ('1-pin-clearance','2-upper-trays'):
            folder=OUT/mode/plate
            try:
                r=check(folder);rows.append(dict(mode=mode,plate=plate,passed=True,interfaces=len(r.get('interfaces',[])),bores=len(r['mount_holes_without_support']),corridors=len(r['free_clip_corridors'])))
            except AssertionError as e:rows.append(dict(mode=mode,plate=plate,passed=False,reason=str(e)))
            print(rows[-1],flush=True)
    for plate in ('2-bodies','2-lids','4-trays'):
        folder=OUT/'batch-two'/plate
        try:
            r=check(folder);rows.append(dict(mode='batch-two',plate=plate,passed=True,interfaces=len(r.get('interfaces',[])),bores=len(r['mount_holes_without_support']),corridors=len(r['free_clip_corridors'])))
        except AssertionError as e:rows.append(dict(mode='batch-two',plate=plate,passed=False,reason=str(e)))
        print(rows[-1],flush=True)
    (OUT/'audit-summary.json').write_text(json.dumps(rows,indent=2))
    assert all(r['passed'] for r in rows), 'Full-product audit failed; see audit-summary.json'

if __name__=='__main__':main()
