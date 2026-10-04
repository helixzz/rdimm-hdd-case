"""Final RC6 plate: solid support starts, roof coverage and true bare control."""
import hashlib,json
import numpy as np
from build_trial_v4_4_rc6 import ROOT,VERSION,parts,solid,v
from audit_sparse_peel_v4_4 import insert_paths,roof_span
from audit_solid_support_v4_4_rc6 import start_check
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint

def bare_roof(paths,record,translation):
    a,b=record['contact_x_mm'];y0=record['ribs'][0][0];y1=sum(record['ribs'][-1])
    tx,ty,tz=translation;rect=[tx+a+.05,ty+y0+.1,tx+b-.05,ty+y1-.1]
    xx,yy=grid(rect);p=select(paths,rect);z=tz+record['contact_z_mm'][1]
    roof=np.zeros(xx.shape,bool);under=roof.copy()
    candidates=p[(p[:,7]==0)&(p[:,8]==0)&(p[:,4]>z+.001)]
    assert len(candidates);first_z=float(candidates[:,4].min())
    for line in candidates[abs(candidates[:,4]-first_z)<.001]:roof|=footprint(line[:8],xx,yy)
    below=p[abs(p[:,4]-(first_z-.2))<.011]
    for line in below:under|=footprint(line[:8],xx,yy)
    assert roof.any()
    return dict(kind=record['kind'],first_roof_z_mm=first_z,previous_layer_overlap_fraction=float((roof&under).sum()/roof.sum()),
        limits='Local contact-face sampling, not full-roof anchoring or sag prediction.')

def main():
    folder=ROOT/f'build/v{VERSION}-projects';plate=folder/'0-dual';qs,_=parts()
    report=json.loads((folder/'slicing-report.json').read_text());geometry=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())
    path=plate/'plate_1.gcode';paths,features=parse_materials(path,excluded_features=('Custom','Flush'));features=np.array(features)
    tower=paths[features=='Prime tower'];assert len(tower)
    lo=(np.minimum(tower[:,:2],tower[:,2:4])-tower[:,5:6]/2).min(0);hi=(np.maximum(tower[:,:2],tower[:,2:4])+tower[:,5:6]/2).max(0)
    gaps=[]
    for volume in geometry['volumes']:
        a,b=np.array(volume['bounds'])[:,:2];gap=np.maximum(0,np.maximum(a-hi,lo-b));assert np.any(gap>0);gaps.append(float(np.linalg.norm(gap)))
    assert (np.minimum(paths[:,:2],paths[:,2:4])-paths[:,5:6]/2).min()>=0
    assert (np.maximum(paths[:,:2],paths[:,2:4])+paths[:,5:6]/2).max()<=256
    paths=paths[features!='Prime tower'];rows=[];starts=[];roofs=[];free=[];bare=[]
    for q in qs:
        for i,s in enumerate(q['interfaces']):
            name=q['name']+'-'+q['insert_records'][i]['kind'];shape=s.translate(q['translation'])
            row=insert_paths(paths,shape,v.m.Manifold(),name)
            assert all(x['dedicated_components']==1 for x in row['layers']);rows.append(row)
            starts.append(start_check(paths,shape,name));matrix=np.eye(4);matrix[:3,3]=q['translation']
            roof=roof_span(paths,dict(q['insert_records'][i],max_clear_gap_mm=.15),matrix)
            assert roof['roof_support_coverage']>.75,(name,roof)
            roofs.append(dict(name=name,**roof,max_allowed_bead_gap_mm=.5))
        tx,ty,_=q['translation']
        if q['kind'].startswith('dimm'):
            rect=[tx+141.35,ty+18.3,tx+141.75,ty+27.5];xx,yy=grid(rect)
            p=select(paths,rect);p=p[(p[:,4]>.2)&(p[:,4]-p[:,6]<6.1)]
            assert not any(footprint(s[:8],xx,yy).any() for s in p);free.append(q['name'])
        if q['name']=='N':
            a,b=np.array(q['model'].bounding_box()).reshape(2,3)+q['translation'];p=select(paths,[*a[:2],*b[:2]])
            assert np.all(p[:,7]==0) and np.all(p[:,8]==0),'N contains automatic/dedicated support'
            for moving in (False,True):bare.append(bare_roof(paths,solid.dimm(moving,.8)[1],q['translation']))
    assert len(rows)==4 and len(bare)==2
    auto=paths[paths[:,7]==1];assert np.all(auto[:,8]==0)
    digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==report['gcode_sha256']
    result=dict(version=VERSION,project_sha256=report['project_sha256'],gcode_sha256=digest,inserts=rows,starts=starts,roofs=roofs,
        free_spring_corridors=free,bare_control=dict(automatic_support_segments=0,dedicated_support_segments=0,roof_samples=bare),
        tower_xy_bounds=[lo.tolist(),hi.tolist()],tower_min_model_bbox_gap_mm=min(gaps),physical_verified=False,
        limits='Every-layer continuity and projected underlying PLA coverage; not adhesion, thermal simulation, peeling or force qualification.')
    (folder/'toolpath-audit.json').write_text(json.dumps(result,indent=2));print('PASS four continuous pads; N genuinely has no support',flush=True)

if __name__=='__main__':main()
