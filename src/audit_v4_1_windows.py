"""Check that the RC2 arch roofs add no supports above the release clips."""
import hashlib
import json
import numpy as np
from pathlib import Path
from audit_v3_2_toolpaths import parse,select,footprint

ROOT=Path(__file__).resolve().parents[1]


def main(version='4.1-rc2-p2',baseline='4.1-rc2-p1'):
    rows=[]
    for current_version in (baseline,version):
        folder=ROOT/f'build/v{current_version}-projects/1-pin-clearance'
        path=folder/'plate_1.gcode'
        s=parse(path);s[:,[0,2]]-=54.5;s[:,[1,3]]-=20
        counts={};closures=[]
        for y in (19.7,55.1):
            # Broad box includes the wall, opening and outward-moving latch.
            high=s[(s[:,7]==1)&(s[:,4]>10.8)&(s[:,4]-s[:,6]<24.4)]
            count=len(select(high,[140,y,148,y+19]))
            if current_version==version:assert count==0,(y,count)
            else:assert count>0,(y,'positive control failed')
            counts[str(y)]=count
            if current_version==version:
                model=select(s[s[:,7]==0],[145.4,y+7,147,y+12])
                cy=y+9.5
                crossing=model[(np.minimum(model[:,1],model[:,3])<cy)&(np.maximum(model[:,1],model[:,3])>cy)&(model[:,4]>19)&(model[:,4]<21)]
                z=float(crossing[:,4].min());current=crossing[crossing[:,4]==z]
                previous_z=float(model[model[:,4]<z-.001,4].max())
                previous=model[abs(model[:,4]-previous_z)<.001]
                gaps=[]
                for segment in current:
                    assert abs(segment[0]-segment[2])<.001,'Expected Y-directed closure'
                    yy=np.arange(y+7,y+12,.002);xx=np.full_like(yy,segment[0])
                    covered=np.zeros_like(yy,dtype=bool)
                    for bead in previous:covered|=footprint(bead,xx,yy)
                    hole=yy[~covered];gap=float(hole.max()-hole.min()+.002)
                    assert gap<1.2,(y,gap)
                    gaps.append(gap)
                assert len(gaps)>=4,(y,'missing closure paths')
                closures.append({'window_y':y,'first_closing_layer_z_mm':z,'previous_layer_z_mm':previous_z,
                    'closure_paths':len(gaps),'max_nominal_previous_layer_gap_mm':round(max(gaps),3),'sampling_mm':.002})
        project=next(folder.glob('*P2S*.3mf'))
        rows.append({'version':current_version,'high_window_support_segments':counts,'closure_spans':closures,
            'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest()})
    result={'results':rows,'arch_shoulders_degrees':45,'rounded_apex_max_chord_mm':1.415,
        'method':'Conservative XY bead boxes and layer Z intervals in both windows above Z10.8; unpainted arch positive control.',
        'limits':'Nominal paths only; first physical arch finish and hand access remain unverified.'}
    (ROOT/f'build/v{version}-projects/window-audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='4.1-rc2-p2')
    parser.add_argument('--baseline',default='4.1-rc2-p1')
    a=parser.parse_args();main(a.version,a.baseline)
