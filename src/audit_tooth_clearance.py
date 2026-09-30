"""Audit printed model gap below all eight DIMM teeth, including local supports."""
import json
import hashlib
from pathlib import Path
import numpy as np
from audit_v3_2_toolpaths import parse,select,footprint

ROOT=Path(__file__).resolve().parents[1]


def main(version='4.2'):
    folder=ROOT/f'build/v{version}-projects'
    checks=json.loads((ROOT/f'models/v{version}/tray-root-fix.json').read_text())['tooth_frame_clearance_checks']
    records=json.loads((ROOT/f'models/v{version}/verification.json').read_text())['plate_records']
    rows=[];sources={}
    for plate in ('1-pin-clearance','2-upper-trays'):
        segs=parse(folder/plate/'plate_1.gcode')
        sources[plate]=hashlib.sha256((folder/plate/'plate_1.gcode').read_bytes()).hexdigest()
        poses=next(r for r in records if r['stem'].endswith('plate-'+plate))['poses']
        for check in checks:
            pose=next((p for p in poses if p['part']==check['part']),None)
            if pose is None:continue
            t=np.array(pose['assembly_to_plate']);assert np.allclose(t[:3,:3],np.eye(3))
            x0=140.65+t[0,3];y0=check['tooth_y']+14.+t[1,3]
            z=4. if check['part'].startswith('body') else 0.
            rect=[x0,y0,x0+.3,y0+4.]
            xx,yy=np.meshgrid(np.arange(rect[0],rect[2],.05),np.arange(rect[1],rect[3],.05))
            near=select(segs,rect)
            frame=np.full(xx.shape,-np.inf);head=np.full(xx.shape,np.inf)
            for s in near[(near[:,7]==0)&(near[:,4]<z+4.5)]:
                hit=footprint(s,xx,yy);frame[hit]=np.maximum(frame[hit],s[4])
            for s in near[(near[:,7]==0)&(near[:,4]>=z+4.6)]:
                hit=footprint(s,xx,yy);head[hit]=np.minimum(head[hit],s[4]-s[6])
            valid=np.isfinite(frame)&np.isfinite(head)
            assert valid.all(),('missing frame/tooth coverage',check['part'],check['clip'])
            gap=float((head-frame).min());assert gap>=.59,(check,gap)
            support_gaps=[]
            for s in near[(near[:,7]==1)&(near[:,4]>z+4.)&(near[:,4]<z+4.6)]:
                hit=footprint(s,xx,yy)&valid
                if not hit.any():continue
                lower=float((s[4]-s[6]-frame[hit]).min());upper=float((head[hit]-s[4]).min())
                assert lower>=.19 and upper>=.19,('trapped contact',check,lower,upper)
                support_gaps.append([lower,upper])
            rows.append({'part':check['part'],'clip':check['clip'],'minimum_model_gap_mm':round(gap,4),
                'sampled_area_mm2':round(float(valid.sum()*.05**2),4),
                'support_segments_in_gap':len(support_gaps),
                'minimum_support_clearance_mm':round(min(min(p) for p in support_gaps),4) if support_gaps else None})
    assert len(rows)==8
    (folder/'tooth-clearance-audit.json').write_text(json.dumps({'version':version,'gcode_sha256':sources,'results':rows,
        'method':'0.05 mm nominal bead raster in the fixed-frame/tooth overlap; model and support separated',
        'limits':'Some gaps contain removable interface strands. This does not simulate sagging, adhesion, removal effort or printed friction.'},indent=2))
    print('Eight tooth/frame regions have >=0.6 mm nominal printed model gap; intermediate supports separated >=0.2 mm')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--version',default='4.2')
    main(parser.parse_args().version)
