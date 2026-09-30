"""Nominal bead separation for explicit sacrificial pull pieces and auto supports."""
import hashlib,json
import numpy as np
from build_support_trial_v4_4 import ROOT,VERSION,parts,v,design
from audit_v3_2_toolpaths import parse,select,grid,footprint


def surface_gap(segs,rect,split):
    near=select(segs,rect);xx,yy=grid(rect)
    lower=np.full(xx.shape,-np.inf);upper=np.full(xx.shape,np.inf)
    for s in near[near[:,4]<=split]:
        hit=footprint(s,xx,yy);lower[hit]=np.maximum(lower[hit],s[4])
    for s in near[near[:,4]-near[:,6]>=split]:
        hit=footprint(s,xx,yy);upper[hit]=np.minimum(upper[hit],s[4]-s[6])
    hit=np.isfinite(lower)&np.isfinite(upper);assert hit.any(),('no opposing beads',rect,split)
    assert hit.mean()>.8,('poor opposing coverage',rect,hit.mean())
    return float((upper[hit]-lower[hit]).min())


def main():
    folder=ROOT/f'build/v{VERSION}-projects';path=folder/'0-support-ab/plate_1.gcode'
    segs=parse(path);rows=[]
    for name,dy in [('A',25.),('B',80.)]:
        # Sample the retained bearing lands as well as the relieved middle.
        rois=[('fixed-land',[6.8,15.,7.25,15.5]),('fixed-middle',[6.8,16.,7.25,17.7]),
              ('tooth-land',[139.85,28.55,140.2,29.05]),('tooth-middle',[139.85,29.7,140.2,31.3]),
              ('left-grip-foot',[8.7,15.2,12.5,17.8]),('right-grip-foot',[134.2,28.7,138.,32.2])]
        for title,rect in rois:
            rect=np.array(rect)+[54.5,dy,54.5,dy]
            splits=[.7] if 'foot' in title else [3.1,4.5]
            for split in splits:
                gap=surface_gap(segs,rect,split)
                assert gap>=.19,(name,title,split,gap)
                rows.append({'coupon':name,'region':title,'split_z_mm':split,'minimum_nominal_gap_mm':round(gap,4)})
        # Automatic support remains under the outboard paddle.
        rect=np.array([143.25,28.8,144.1,32.2])+[54.5,dy,54.5,dy]
        near=select(segs,rect);assert np.any((near[:,7]==1)&(near[:,4]>=5.)&(near[:,4]<=5.2))
        gap=surface_gap(segs,rect,5.3);assert gap>=.19,(name,'paddle',gap)
        rows.append({'coupon':name,'region':'automatic-paddle-support','minimum_nominal_gap_mm':round(gap,4)})
    # Controlled residual simulation: a 0.2 mm bump on a non-bearing seat area.
    # Fixed-end patch chosen away from the bearing lands in B.
    result,_=parts();residue=[]
    ram=design.base.rc.simple.module(133.8,31.4,1.37,6.55,2.7)
    for name in ('A','B'):
        seat_z=3. if name=='A' else 2.69
        patch=v.box((.5,2.,.2),(6.8,16.,seat_z))
        collision=(patch^ram).volume()
        if name=='A':assert collision>.1
        else:assert collision<1e-6
        residue.append({'coupon':name,'bump_height_mm':.2,'module_intersection_mm3':collision})
    report={'version':VERSION,'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checks':rows,
        'controlled_seat_residue_test':residue,'limits':'One artificial residue patch only. No thermal sagging, adhesion or removal-force simulation; actual removal and retention need testing.'}
    (folder/'toolpath-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
