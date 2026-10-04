"""Inspect real material paths in sparse ribs and mechanically captured handles."""
import argparse,json
from pathlib import Path
import numpy as np
import study_sparse_peel_v4_4 as study
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint
import audit_full_product as whole

def component_count(mask):
    remaining=set(map(tuple,np.argwhere(mask)));count=0
    while remaining:
        count+=1;todo=[remaining.pop()]
        while todo:
            p=todo.pop()
            for axis in range(len(p)):
              for delta in (-1,1):
                q=list(p);q[axis]+=delta;point=tuple(q)
                if point in remaining:remaining.remove(point);todo.append(point)
    return count

def insert_paths(paths,solid,handle,name):
    lo,hi=np.array(solid.bounding_box()).reshape(2,3)
    rect=[lo[0]-.3,lo[1]-.3,hi[0]+.3,hi[1]+.3]
    local=select(paths,rect);local=local[(local[:,4]>lo[2]+.001)&(local[:,4]<=hi[2]+.11)]
    xx,yy=np.meshgrid(np.arange(rect[0],rect[2],.05),np.arange(rect[1],rect[3],.05))
    layers=[];previous=None;bottom=None;top=None;key_hits=0;masks=[]
    for z in np.unique(local[:,4]):
        support=np.zeros(xx.shape,bool);pla=support.copy()
        for p in local[np.abs(local[:,4]-z)<.001]:
            if p[8]==1:support|=footprint(p[:8],xx,yy)
            elif p[7]==0:pla|=footprint(p[:8],xx,yy)
        if not support.any():continue
        count=component_count(support)
        # First rib layers may be separate while supported on the PLA seat;
        # the rising spine must connect them in the complete 3D bead stack.
        masks.append(support)
        fraction=None if previous is None else float((support&previous).sum()/support.sum())
        if fraction is not None:assert fraction>.45,(name,z,'poor layer overlap',fraction)
        if handle.volume()>0:
            # Witness the printed PLA T shoulders bearing against dedicated
            # material after a nominal .3 mm pull. Restrict to handle bbox.
            h0,h1=np.array(handle.bounding_box()).reshape(2,3)
            direction=-1 if name.endswith('moving') else 1
            hp=pla&(xx>=h0[0]-.1)&(xx<=h1[0]+.1)&(yy>=h0[1]-.1)&(yy<=h1[1]+.1)
            shifted=np.roll(hp,int(direction*6),axis=1)
            key_hits+=int((shifted&support).sum())
        layers.append(dict(z_mm=float(z),dedicated_components=count,previous_layer_overlap_fraction=fraction))
        previous=support;bottom=support if bottom is None else bottom;top=support
    assert len(layers)>=7,(name,'missing insert layers')
    count3d=component_count(np.array(masks));assert count3d==1,(name,'disconnected 3D material',count3d)
    if handle.volume()>0:assert key_hits>3,(name,'no printed mechanical key witness')
    return dict(name=name,layers=layers,connected_3d_dedicated_components=count3d,printed_key_overlap_grid_cells=key_hits,grid_mm=.05)

def roof_span(paths,record,matrix):
    a,b=record['contact_x_mm'];ys=record['ribs'];y0=ys[0][0];y1=ys[-1][0]+ys[-1][1]
    xx,yy=np.meshgrid(np.arange(a+.2,b-.19,.05),np.arange(y0+.15,y1-.14,.05))
    points=np.c_[xx.ravel(),yy.ravel(),np.full(xx.size,record['contact_z_mm'][1])]
    points+=np.array(record.get('shift',[0,0,0]))
    if record.get('mirror'):points[:,0]=147-points[:,0]
    points=points@matrix[:3,:3].T+matrix[:3,3];px=points[:,0].reshape(xx.shape);py=points[:,1].reshape(xx.shape)
    z=points[0,2];local=select(paths,[px.min()-.3,py.min()-.3,px.max()+.3,py.max()+.3]);hit=np.zeros(xx.shape,bool)
    for p in local[(local[:,8]==1)&(abs(local[:,4]-z)<.011)]:hit|=footprint(p[:8],px,py)
    assert hit.mean()>.10,('missing roof support',record)
    longest=0
    for col in hit.T:
        run=0
        for x in col:
            run=0 if x else run+1;longest=max(longest,run)
    gap=round(longest*.05,3)
    assert gap<=record['max_clear_gap_mm']+.35,('unexpected roof support gap',gap,record)
    return dict(kind=record['kind'],roof_support_coverage=float(hit.mean()),max_uncovered_y_run_mm=gap,grid_mm=.05)

def audit_product(folder,gap,keyed=True,split=False):
    if split:
        import study_split_keeper_v4_4 as sp
        plates,_=sp.product()
    else:plates,_=study.product(gap,keyed)
    qs=next(items for label,items in plates if label==folder.name)
    paths,_=parse_materials(folder/'plate_1.gcode');rows=[];spans=[];aux=[]
    for q in qs:
        for i,s in enumerate(q['interfaces']):
            h=q['cores'][i] if keyed else study.v.m.Manifold()
            name=q['name']+'-'+str(i)+'-'+q['insert_records'][i]['kind']
            # Geometry is in print coordinates. Right-hand capture keys pull -X.
            if q['insert_records'][i].get('mirror'):name+='-moving'
            rows.append(insert_paths(paths,s,h,name))
            spans.append(roof_span(paths,q['insert_records'][i],np.linalg.inv(q['inverse'])))
        if q.get('kind')=='keeper':
            a,b=np.array(q['model'].bounding_box()).reshape(2,3)
            p=select(paths,[*a[:2],*b[:2]]);p=p[p[:,7]==1]
            assert len(p)==0,(q['name'],'keeper auto support');aux.append(q['name'])
    old=whole.audit
    try:
        whole.audit=lambda *a,**k:{}
        other=whole.check(folder)
    finally:whole.audit=old
    report=dict(inserts=rows,roof_spans=spans,support_free_keepers=aux,whole_plate=other,physical_verified=False,
        limitations='Nominal material bead connectivity, layer overlap, key interception, bores and free paths; not adhesion/removal force/strength.')
    (folder/'sparse-audit.json').write_text(json.dumps(report,indent=2));print('PASS',folder,len(rows),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gaps',nargs='+',type=float,default=[.8,1.2]);p.add_argument('--split',action='store_true');a=p.parse_args()
    for gap in a.gaps:
        for plate in ('1-pin-clearance','2-upper-trays'):
            folder=(study.ROOT/'build/split-keeper-study' if a.split else study.OUT/f'keyed-gap-{gap}')/plate
            audit_product(folder,gap,split=a.split)
