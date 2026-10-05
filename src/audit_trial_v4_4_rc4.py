"""Actual material, free-corridor, tower and process-override checks for RC4."""
import hashlib,json,shutil
import numpy as np
from build_trial_v4_4_rc4 import ROOT,VERSION
from audit_dfm_study import audit
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint

def main():
    folder=ROOT/f'build/v{VERSION}-projects';plate=folder/'0-dual'
    report=json.loads((folder/'slicing-report.json').read_text())
    geometry=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())
    shutil.copyfile(ROOT/f'models/v{VERSION}/verification.json',plate/'verification.json')
    result=audit(plate,check_settings=False,check_h32=True,project_name=report['project'])
    assert len(result['interfaces'])==14
    path=plate/'plate_1.gcode';p,features=parse_materials(path,excluded_features=('Custom','Flush'));features=np.array(features)
    tower=p[features=='Prime tower'];assert len(tower)
    lo=(np.minimum(tower[:,:2],tower[:,2:4])-tower[:,5:6]/2).min(0)
    hi=(np.maximum(tower[:,:2],tower[:,2:4])+tower[:,5:6]/2).max(0)
    gaps=[]
    for volume in geometry['volumes']:
        a,b=np.array(volume['bounds'])[:,:2];gap=np.maximum(0,np.maximum(a-hi,lo-b))
        assert np.any(gap>0),volume['name'];gaps.append(float(np.linalg.norm(gap)))
    assert (np.minimum(p[:,:2],p[:,2:4])-p[:,5:6]/2).min()>=0
    assert (np.maximum(p[:,:2],p[:,2:4])+p[:,5:6]/2).max()<=256
    active=features!='Prime tower';p=p[active];features=features[active]
    auto=p[p[:,7]==1];assert len(auto) and np.all(auto[:,8]==0),'Ordinary automatic supports must use PLA'
    q=select(p,[188.25,73.2,189.3,78]);q=q[(q[:,7]==1)&(q[:,4]<=5.6)]
    assert not len(q),'Extra automatic support under the strengthened paddle'
    # A retains the first upper-tray anchor shifted +2.8 mm in v4.2.
    # The fixed 3 mm anchor is intentionally solid; check only the free span.
    rect=[186.35,63.3,186.75,72.5];xx,yy=grid(rect)
    q=select(p,rect);q=q[(q[:,4]>.2)&(q[:,4]-q[:,6]<6.1)]
    assert not any(footprint(s[:8],xx,yy).any() for s in q),'Filled spring corridor'
    samples={}
    for name,x in [('P1',45),('P2',115)]:
        inside=(p[:,0]>=x-.1)&(p[:,0]<=x+50.1)&(p[:,1]>=169.9)&(p[:,1]<=186.1)
        sample={}
        for feature in ('Sparse infill','Internal solid infill','Top surface','Outer wall'):
            s=p[inside&(features==feature)];assert len(s),(name,feature)
            assert np.all(s[:,8]==0)
            sample[feature]=dict(segments=len(s),widths_mm=np.unique(s[:,5]).tolist(),heights_mm=np.unique(s[:,6]).tolist())
        samples[name]=sample
    assert samples['P1']['Sparse infill']['heights_mm']==[.2]
    assert samples['P2']['Sparse infill']['heights_mm']==[.2,.4]
    assert samples['P1']['Sparse infill']['widths_mm']==[.45]
    assert samples['P2']['Sparse infill']['widths_mm']==[.5]
    for name in samples:
        assert samples[name]['Top surface']['widths_mm']==[.42]
        assert samples[name]['Top surface']['heights_mm']==[.2]
        assert samples[name]['Outer wall']['widths_mm']==[.42,.5]
        assert samples[name]['Outer wall']['heights_mm']==[.2]
    text=path.read_text(encoding='utf8');assert 'M620 S0A' in text and 'M620 S1A' in text
    assert 'M600' not in '\n'.join(s for s in text.splitlines() if not s.startswith(';'))
    digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==report['gcode_sha256']
    result.update(version=VERSION,gcode_sha256=digest,project_sha256=report['project_sha256'],automatic_support_material='PLA',
        automatic_support_under_paddle=0,free_spring_corridor=True,process_samples=samples,
        tower_xy_bounds=[lo.tolist(),hi.tolist()],tower_min_model_bbox_gap_mm=min(gaps),ams_changes_present=True,
        physical_verified=False,limits='Nominal toolpaths and material identity, not removal force, adhesion, warpage, fatigue or strength.')
    (folder/'toolpath-audit.json').write_text(json.dumps(result,indent=2))
    print('PASS: 14 interfaces; 2 empty holes; clear spring; 2 real process variants; tower gap',min(gaps))

if __name__=='__main__':main()
