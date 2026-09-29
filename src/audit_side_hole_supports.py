"""Conservative bead-envelope audit of six side bores before/after support paint."""
import hashlib
import json
from pathlib import Path
from audit_v3_2_toolpaths import parse,select
from build_v3 import SIDE_X,W

ROOT=Path(__file__).resolve().parents[1]


def run(version='4.0-rc4-p1',baseline='4.0-rc4'):
    results=[]
    for current in (baseline,version):
        path=ROOT/f'build/v{current}-projects/1-pin-clearance/plate_1.gcode'
        segs=parse(path)
        segs[:,[0,2]]-=54.5
        segs[:,[1,3]]-=20
        segs=segs[(segs[:,7]==1)&(segs[:,4]>4.55)&(segs[:,4]-segs[:,6]<8.15)]
        counts={}
        for x in SIDE_X:
            for side,lo,hi in [('front',0,5.7),('back',W-5.7,W)]:
                counts[f'{x}-{side}']=len(select(segs,[x-1.8,lo,x+1.8,hi]))
        if current==version:assert not any(counts.values()),counts
        else:assert all(counts.values()),counts
        results.append({'version':current,'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'support_segments_overlapping_bore_bounding_boxes':counts})
    report={'method':'Conservative bounding boxes include nominal bead width and layer height; arcs discretized at <=0.05 mm. Zero proves absence in the enclosed bores, not physical roof quality.',
            'results':results,'physical_pin_fit_verified':False}
    out=ROOT/f'build/v{version}-projects/side-hole-audit.json'
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='4.0-rc4-p1')
    parser.add_argument('--baseline',default='4.0-rc4')
    args=parser.parse_args();run(args.version,args.baseline)
