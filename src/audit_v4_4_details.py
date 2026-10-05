"""Fresh permanent PLA root/tooth and remaining ordinary support checks."""
import hashlib,json
import numpy as np
from build_v4_4 import ROOT,VERSION
from audit_dual_trial_v4_4_rc3 import parse_materials,select,grid,footprint
from audit_v3_2_toolpaths import transformed_rect
import audit_tray_roots as roots
import audit_tooth_clearance as teeth

def classified(path):
    p,_=parse_materials(path)
    p[:,7]=np.maximum(p[:,7],p[:,8]==1)
    return p[:,:8]

def main(version=VERSION):
    VERSION=version
    folder=ROOT/f'build/v{VERSION}-projects'
    # Dedicated Support is emitted as MODEL by Studio. It must not count as
    # permanent root material or fill an apparent permanent tooth clearance.
    old=roots.parse,teeth.parse
    try:
        roots.parse=classified;teeth.parse=classified
        roots.main(VERSION);teeth.main(VERSION)
    finally:roots.parse,teeth.parse=old
    records=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())['plate_records']
    path=folder/'1-pin-clearance/plate_1.gcode';p=classified(path);checks=[]
    poses=records[0]['poses'];body=next(x for x in poses if x['part'].startswith('body'));lid=next(x for x in poses if x['part'].startswith('lid'))
    t=np.array(body['assembly_to_plate'])
    rois=[('shell latch',[49,0,77,1.6],22.8),('SATA roof',[0,43.6,7.5,90.6],6.2)]
    from build_v4_4 import v,solid
    for i,sy in enumerate(v.layout(2)[2]):
        y=solid.base.rc.simple.clip_start(2,i,sy)
        rois.append((f'bottom beam foot {i+1}',[142.,y+1,142.8,y+13],4.))
    regions=[(n,transformed_rect(r,t),z+t[2,3]) for n,r,z in rois]
    t=np.array(lid['assembly_to_plate'])
    for y,length in [(8.,6.),(95.6,4.2)]:
        for x in (3.5,140.8):regions.append((f'lid tongue {x}/{y}',transformed_rect([x,y+.55,x+2.7,y+length-.85],t),2.4))
    for name,rect,z in regions:
        near=select(p,rect);xx,yy=grid(rect);top=np.full(xx.shape,-np.inf);bottom=np.full(xx.shape,np.inf)
        for line in near[(near[:,7]==1)&(near[:,4]>=z-.5)&(near[:,4]<z-.05)]:
            hit=footprint(line,xx,yy);top[hit]=np.maximum(top[hit],line[4])
        for line in near[(near[:,7]==0)&(near[:,4]-near[:,6]>=z-.05)&(near[:,4]-near[:,6]<z+.4)]:
            hit=footprint(line,xx,yy);bottom[hit]=np.minimum(bottom[hit],line[4]-line[6])
        overlap=np.isfinite(top)&np.isfinite(bottom);assert overlap.any(),(name,'missing support')
        gap=float((bottom[overlap]-top[overlap]).min());assert gap>=.19,(name,gap)
        checks.append(dict(region=name,nominal_z_gap_mm=gap,sampled_overlap_fraction=float(overlap.mean())))
    rect=transformed_rect([77.3,.1,77.7,1.5],np.array(body['assembly_to_plate']));xx,yy=grid(rect)
    near=select(p,rect);near=near[(near[:,4]>23.01)&(near[:,4]-near[:,6]<25.99)]
    assert not any(footprint(line,xx,yy).any() for line in near)
    out=dict(version=VERSION,gcode_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),ordinary_support_regions=checks,
             shell_latch_free_corridor=True,limits='Nominal beads only, not adhesion, force, fatigue or thermal deformation.')
    (folder/'ordinary-support-audit.json').write_text(json.dumps(out,indent=2));print('PASS eight ordinary support regions and shell latch corridor')

if __name__=='__main__':main()
