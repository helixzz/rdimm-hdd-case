"""Conservative bead-envelope audit of six side bores before/after support paint."""
import hashlib
import json
from pathlib import Path
from audit_v3_2_toolpaths import parse,select
from build_v3 import SIDE_X,W

ROOT=Path(__file__).resolve().parents[1]


def run():
    results=[]
    for version in ('4.0-rc4','4.0-rc4-p1'):
        path=ROOT/f'build/v{version}-projects/1-pin-clearance/plate_1.gcode'
        segs=parse(path)
        segs[:,[0,2]]-=54.5
        segs[:,[1,3]]-=20
        segs=segs[(segs[:,7]==1)&(segs[:,4]>4.55)&(segs[:,4]-segs[:,6]<8.15)]
        counts={}
        for x in SIDE_X:
            for side,lo,hi in [('front',0,5.7),('back',W-5.7,W)]:
                counts[f'{x}-{side}']=len(select(segs,[x-1.8,lo,x+1.8,hi]))
        if version.endswith('-p1'):assert not any(counts.values()),counts
        else:assert all(counts.values()),counts
        results.append({'version':version,'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'support_segments_overlapping_bore_bounding_boxes':counts})
    report={'method':'Conservative bounding boxes include nominal bead width and layer height; arcs discretized at <=0.05 mm. Zero proves absence in the enclosed bores, not physical roof quality.',
            'results':results,'physical_pin_fit_verified':False}
    out=ROOT/'build/v4.0-rc4-p1-projects/side-hole-audit.json'
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':run()
