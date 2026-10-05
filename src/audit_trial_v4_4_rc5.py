"""Final plate: connected dedicated inserts, mounts, support-free keeper and paths."""
import hashlib,json
import numpy as np
from build_trial_v4_4_rc5 import ROOT,VERSION,parts
from audit_sparse_peel_v4_4 import insert_paths,roof_span
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint
from evaluate_rc4_feedback import count_bores

def main():
    folder=ROOT/f'build/v{VERSION}-projects';plate=folder/'0-dual'
    report=json.loads((folder/'slicing-report.json').read_text());qs,_=parts()
    geometry=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())
    path=plate/'plate_1.gcode';paths,features=parse_materials(path,excluded_features=('Custom','Flush'));features=np.array(features)
    tower=paths[features=='Prime tower'];assert len(tower)
    lo=(np.minimum(tower[:,:2],tower[:,2:4])-tower[:,5:6]/2).min(0);hi=(np.maximum(tower[:,:2],tower[:,2:4])+tower[:,5:6]/2).max(0)
    gaps=[]
    for volume in geometry['volumes']:
        a,b=np.array(volume['bounds'])[:,:2];gap=np.maximum(0,np.maximum(a-hi,lo-b));assert np.any(gap>0),volume['name'];gaps.append(float(np.linalg.norm(gap)))
    assert (np.minimum(paths[:,:2],paths[:,2:4])-paths[:,5:6]/2).min()>=0
    assert (np.maximum(paths[:,:2],paths[:,2:4])+paths[:,5:6]/2).max()<=256
    paths=paths[features!='Prime tower'];rows=[];spans=[];free=[];keeper_support=[]
    for q in qs:
        for i,s in enumerate(q['interfaces']):
            name=q['name']+'-'+q['insert_records'][i]['kind']
            rows.append(insert_paths(paths,s.translate(q['translation']),q['cores'][i].translate(q['translation']),name))
            matrix=np.eye(4);matrix[:3,3]=q['translation'];spans.append(dict(name=name,**roof_span(paths,q['insert_records'][i],matrix)))
        tx,ty,_=q['translation']
        if q['kind']=='dimm':
            rect=[tx+141.35,ty+18.3,tx+141.75,ty+27.5];xx,yy=grid(rect)
            p=select(paths,rect);p=p[(p[:,4]>.2)&(p[:,4]-p[:,6]<6.1)]
            assert not any(footprint(s[:8],xx,yy).any() for s in p),(q['name'],'spring corridor')
            free.append(q['name'])
        if q['name']=='B-KEEPER':
            a,b=np.array(q['model'].bounding_box()).reshape(2,3)+q['translation']
            p=select(paths,[*a[:2],*b[:2]]);p=p[p[:,7]==1]
            assert len(p)==0,'Support generated inside separate keeper'
            keeper_support.append(dict(name=q['name'],automatic_support_segments=len(p)))
        if q['name']=='B':
            p=select(paths,[tx+1.8,ty+14.4,tx+8.0,ty+49.0]);p=p[p[:,7]==1]
            assert len(p)==0,'Support generated at B fixed-end mounts'
            keeper_support.append(dict(name='B fixed end',automatic_support_segments=len(p)))
    holes=[('H32','side',150,125,6.35),('H32','bottom',160,128.175,0),
           ('P1','side',80.104,170,6.35),('P1','bottom',51.275,173.175,0)]
    bores=count_bores(paths,holes);assert all(r['automatic_support_segments']==0 for r in bores)
    assert len(rows)==5
    text=path.read_text();assert 'M620 S0A' in text and 'M620 S1A' in text
    auto=paths[paths[:,7]==1];assert np.all(auto[:,8]==0)
    digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==report['gcode_sha256']
    result=dict(version=VERSION,project_sha256=report['project_sha256'],gcode_sha256=digest,inserts=rows,
        bores=bores,roof_spans=spans,free_spring_corridors=free,split_keeper_support=keeper_support,automatic_support_material='PLA',
        tower_xy_bounds=[lo.tolist(),hi.tolist()],tower_min_model_bbox_gap_mm=min(gaps),physical_verified=False,
        limits='Geometry and nominal material paths; no adhesion, removal force, warpage, fit tolerance, strength or fatigue simulation.')
    (folder/'toolpath-audit.json').write_text(json.dumps(result,indent=2));print('PASS',len(rows),'connected inserts, 4 empty bores, B fixed end/keeper no support',flush=True)

if __name__=='__main__':main()
