"""Check that the sliced identification grooves survive on all four parts."""
import hashlib,json
import numpy as np
from build_v4_4_1 import ROOT,VERSION,parts,marks,DEPTH
from audit_dual_trial_v4_4_rc3 import parse_materials,select,footprint

def main():
    plates,_=parts();records=[]
    for label,items in plates:
        path=ROOT/f'build/v{VERSION}-projects'/label/'plate_1.gcode';paths,_=parse_materials(path)
        for q in items:
            pose=np.linalg.inv(q['inverse'])
            for text,shape,t,surface,_ in marks(q['name']):
                polys=shape.offset(-.15).to_polygons();vertices=np.concatenate(polys)
                (a,b),(c,d)=vertices.min(0),vertices.max(0)
                xx,yy=np.meshgrid(np.arange(a,c,.06),np.arange(b,d,.06));inside=np.zeros(xx.shape,bool)
                for poly in polys:
                    for (x0,y0),(x1,y1) in zip(poly,np.roll(poly,-1,axis=0)):
                        if abs(y1-y0)>1e-12:inside^=((y0>yy)!=(y1>yy))&(xx<(x1-x0)*(yy-y0)/(y1-y0)+x0)
                points=np.c_[xx[inside],yy[inside],np.full(inside.sum(),DEPTH/2),np.ones(inside.sum())]
                tr=np.eye(4);tr[:3,:]=t;world=points@(pose@tr).T;x,y,z=world[:,:3].T
                near=select(paths,[x.min()-.6,y.min()-.6,x.max()+.6,y.max()+.6]);near=near[(near[:,4]>z[0])&(near[:,4]-near[:,6]<z[0])]
                assert len(near)>10,(q['name'],text,'missing surrounding layer')
                filled=np.zeros(len(x),bool);support=np.zeros(len(x),bool)
                for line in near:
                    hit=footprint(line[:8],x,y);filled|=hit
                    if line[7] or line[8]==1:support|=hit
                fraction=float(filled.mean());assert fraction<.12,(q['name'],text,'groove filled',fraction)
                assert not support.any(),(q['name'],text,'support in groove')
                records.append(dict(part=q['name'],text=text,surface=surface,samples=len(x),nominal_bead_coverage=fraction,support_in_groove=False,gcode_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assert len({r['part'] for r in records})==4
    out=dict(version=VERSION,marks=records,limits='Nominal bead footprints; texture, legibility and first-layer spreading require printing.')
    (ROOT/f'build/v{VERSION}-projects/version-mark-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

if __name__=='__main__':main()

