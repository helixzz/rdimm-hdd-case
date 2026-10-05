"""Audit dense support starts, every-layer continuity and supported roofs."""
import argparse,json,hashlib
import numpy as np
import study_solid_support_v4_4_rc6 as r
from audit_sparse_peel_v4_4 import insert_paths,roof_span,component_count
from audit_dual_trial_v4_4_rc3 import parse_materials,select,footprint
import audit_full_product as whole

def start_check(paths,solid,name):
    lo,hi=np.array(solid.bounding_box()).reshape(2,3)
    rect=[lo[0]-.3,lo[1]-.3,hi[0]+.3,hi[1]+.3]
    p=select(paths,rect);p=p[(p[:,4]>lo[2]-.4)&(p[:,4]<hi[2]+.2)]
    sp=p[(p[:,8]==1)&(p[:,4]>lo[2]+.001)]
    z=sp[:,4].min();first=sp[abs(sp[:,4]-z)<.001]
    xx,yy=np.meshgrid(np.arange(rect[0],rect[2],.05),np.arange(rect[1],rect[3],.05))
    mask=np.zeros(xx.shape,bool);below=mask.copy()
    for line in first:mask|=footprint(line[:8],xx,yy)
    bottom=z-float(first[0,6]);prior=p[(p[:,8]==0)&(abs(p[:,4]-bottom)<.011)]
    for line in prior:below|=footprint(line[:8],xx,yy)
    ratio=float((mask&below).sum()/mask.sum())
    assert component_count(mask)==1,(name,'first-layer islands')
    assert ratio>.55,(name,'low underlying PLA coverage',ratio)
    return dict(name=name,first_z_mm=float(z),first_layer_area_mm2=float(mask.sum()*.05**2),
        first_layer_components=1,underlying_PLA_coverage=ratio,grid_mm=.05,
        limitation='Projected bead overlap, not adhesion or resistance to nozzle drag.')

def audit(items,folder):
    paths,features=parse_materials(folder/'plate_1.gcode');features=np.array(features)
    paths=paths[(features!='Prime tower')&(features!='Flush')&(features!='Custom')]
    rows=[];starts=[];roofs=[]
    for q in items:
        for i,solid in enumerate(q['interfaces']):
            name=q['name']+'-'+str(i)
            row=insert_paths(paths,solid,r.v.m.Manifold(),name)
            assert all(x['dedicated_components']==1 for x in row['layers']),(name,'layer islands')
            rows.append(row);starts.append(start_check(paths,solid,name))
            # Dense CAD can retain a seam-sized bead gap. Allow at most .5 mm
            # (about one nominal .42 mm extrusion plus grid/edge rounding),
            # explicitly report the actual gap instead of claiming full cover.
            rec=dict(q['insert_records'][i],max_clear_gap_mm=.15)
            roof=roof_span(paths,rec,np.linalg.inv(q['inverse']))
            assert roof['roof_support_coverage']>.75,(name,'low dense roof coverage',roof)
            roof['max_allowed_bead_gap_mm']=.5;roofs.append(roof)
    old=whole.audit
    try:whole.audit=lambda *a,**k:{};wp=whole.check(folder)
    finally:whole.audit=old
    report=dict(inserts=rows,starts=starts,roofs=roofs,whole_plate=wp,
        gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),physical_verified=False)
    (folder/'solid-audit.json').write_text(json.dumps(report,indent=2));print('PASS',folder,len(rows),flush=True)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--heights',nargs='+',type=float,default=[5.,5.4]);a=ap.parse_args()
    for h in a.heights:
        plates,_=r.product(h)
        for label,items in plates:audit(items,r.ROOT/f'build/rc6-solid-study/grip-{h:.1f}'/label)
