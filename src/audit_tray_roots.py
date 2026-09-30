"""Check V4.2 clip-root model beads connect across the joint without support."""
import json
from pathlib import Path
import numpy as np
from audit_v3_2_toolpaths import parse,select,footprint

ROOT=Path(__file__).resolve().parents[1]


def label(mask):
    out=np.zeros(mask.shape,dtype=int);n=0
    for row,col in zip(*np.nonzero(mask)):
        if out[row,col]:continue
        n+=1;stack=[(row,col)];out[row,col]=n
        while stack:
            a,b=stack.pop()
            for c,d in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                if 0<=c<mask.shape[0] and 0<=d<mask.shape[1] and mask[c,d] and not out[c,d]:
                    out[c,d]=n;stack.append((c,d))
    return out,n


def main():
    folder=ROOT/'build/v4.2-projects'
    segs=parse(folder/'2-upper-trays/plate_1.gcode')
    records=json.loads((ROOT/'models/v4.2/verification.json').read_text())['plate_records']
    poses=next(r for r in records if r['stem'].endswith('plate-2-upper-trays'))['poses']
    roots=json.loads((ROOT/'models/v4.2/tray-root-fix.json').read_text())['root_checks']
    checks=[]
    for root in roots:
        pose=next(p for p in poses if p['part']==root['part'])
        t=np.array(pose['assembly_to_plate']);assert np.allclose(t[:3,:3],np.eye(3))
        x=142.+t[0,3];y=root['root_y']+t[1,3]
        rect=[x-.3,y-1.1,x+1.5,y+1.1]
        xx,yy=np.meshgrid(np.arange(rect[0],rect[2],.05),np.arange(rect[1],rect[3],.05))
        near=select(segs,rect)
        for z in np.arange(.2,6.21,.2):
            model=near[(near[:,7]==0)&(np.abs(near[:,4]-z)<.001)]
            mask=np.zeros(xx.shape,dtype=bool)
            for s in model:mask|=footprint(s,xx,yy)
            components,n=label(mask)
            a=np.unique(components[(xx>x+.1)&(xx<x+.7)&(yy>y-.8)&(yy<y-.4)])
            b=np.unique(components[(xx>x+.1)&(xx<x+.7)&(yy>y+.3)&(yy<y+.7)])
            joined=set(a)&set(b)-{0}
            assert joined,(root['part'],root['clip'],z,'no model-bead path across root')
            checks.append({'part':root['part'],'clip':root['clip'],'layer_top_z':round(float(z),3),'connected_model_only':True})
    report={'version':'4.2','method':'0.05 mm raster of nominal model extrusion beads, 4-neighbour connectivity; support beads excluded',
        'limits':'Nominal bead paths do not measure weld strength, adhesion, cooling or fatigue. Not physical validation.',
        'checks':checks}
    (folder/'root-bead-audit.json').write_text(json.dumps(report,indent=2))
    print(len(checks),'model-only layer/root connections verified')


if __name__=='__main__':main()
