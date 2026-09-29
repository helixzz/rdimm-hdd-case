"""Use the locally generated RC1 public presets for the RC2 coupon base."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile
import numpy as np
from check_bambu_v3 import read_mesh, components
from prepare_v3_2_project import OVERRIDES
from audit_v3_2_toolpaths import parse,select,grid,footprint,side_gap

ROOT=Path(__file__).resolve().parents[1]


def run(args):
    out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    preset=args.rc1_projects/'0-checks'
    process=json.loads((preset/'process.json').read_text())
    assert all(process[k]==v for k,v in OVERRIDES.items())
    process.update(name='RDIMM RC2 A coupon - supports required',print_settings_id='RDIMM RC2 A coupon - supports required')
    (out/'process.json').write_text(json.dumps(process),encoding='utf8')
    stem='rdimm-3.2-rc2-plate-A-base-only'
    source=(args.models/(stem+'.3mf')).resolve()
    target=out/(stem+'-P2S-PLA-Basic.3mf')
    commands=[
        [str(args.bambu),'--arrange','0','--load-settings',str((preset/'machine.json').resolve())+';'+str(out/'process.json'),
         '--load-filaments',str((preset/'filament.json').resolve()),'--curr-bed-type','Textured PEI Plate','--export-3mf',str(target),str(source)],
        [str(args.bambu),'--arrange','0','--slice','0','--outputdir',str(out),str(target)],
    ]
    for i,cmd in enumerate(commands):
        p=subprocess.run(cmd,cwd=out,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (out/f'cli-{i}.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(i,p.returncode)
    result=json.loads((out/'result.json').read_text())
    assert result['return_code']==0 and len(result['sliced_plates'])==1
    assert '; EXECUTABLE_BLOCK_END' in (out/'plate_1.gcode').read_text(encoding='utf8')
    with zipfile.ZipFile(target) as z:
        config=json.loads(z.read('Metadata/project_settings.config'))
        assert all(config[k]==v for k,v in OVERRIDES.items())
    before,after=read_mesh(source),read_mesh(target)
    assert np.allclose(before.bounds,after.bounds,atol=.0002)
    assert abs(before.volume-after.volume)<.05
    assert components(before)==components(after)==1
    plate=result['sliced_plates'][0]
    report={'version':'3.2-rc2','scope':'A coupon base only','project':target.name,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'estimated_seconds':plate['total_predication'],'grams':plate['filaments'][0]['total_used_g'],
            'warnings':plate['warning_message'],'physical_tested':False}
    segs=parse(out/'plate_1.gcode')
    # Assembly-to-plate translation is [65,110,-19.2]. The slide channel
    # above each new lower bearing must not acquire support material.
    channel_results=[]
    for name,rect in [('left',[99.65,111.8,101.2,130.8]),('right',[154.8,111.8,156.35,130.8])]:
        candidates=select(segs,rect)
        candidates=candidates[(candidates[:,7]==1)&(candidates[:,4]>5.001)&(candidates[:,4]-candidates[:,6]<6.8)]
        xx,yy=grid(rect)
        hits=sum(footprint(s,xx,yy).any() for s in candidates)
        assert hits==0,('Support fills lower rail slide channel',name)
        channel_results.append({'rail':name,'support_intrusions_above_bearing':int(hits)})
    rect=[112.5,110.,142.,111.6]; roof=3.8
    nearby=select(segs,rect);xx,yy=grid(rect)
    top=np.full(xx.shape,-np.inf);bottom=np.full(xx.shape,np.inf)
    for s in nearby[(nearby[:,7]==1)&(nearby[:,4]>=roof-.5)&(nearby[:,4]<roof-.05)]:
        hit=footprint(s,xx,yy);top[hit]=np.maximum(top[hit],s[4])
    for s in nearby[(nearby[:,7]==0)&(nearby[:,4]-nearby[:,6]>=roof-.05)&(nearby[:,4]-nearby[:,6]<roof+.4)]:
        hit=footprint(s,xx,yy);bottom[hit]=np.minimum(bottom[hit],s[4]-s[6])
    overlap=np.isfinite(top)&np.isfinite(bottom)
    assert overlap.any()
    gap=float(np.min(bottom[overlap]-top[overlap]));assert gap>=.19
    side=side_gap(segs,rect,roof-2,roof+.6);assert side is None or side>.10
    report['support_audit']={'channels':channel_results,'leaf_min_nominal_z_gap_mm':round(gap,4),'leaf_min_local_xy_gap_mm':side,
                             'method':'Actual variable line width/layer height; nominal bead projection, not physical simulation'}
    (out/'slicing-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bambu',type=Path,required=True)
    p.add_argument('--models',type=Path,default=ROOT/'models/v3.2-rc2-latch-check')
    p.add_argument('--rc1-projects',type=Path,default=ROOT/'build/v3.2-rc1-projects')
    p.add_argument('--output-dir',type=Path,default=ROOT/'build/v3.2-rc2-latch-check-project')
    run(p.parse_args())
