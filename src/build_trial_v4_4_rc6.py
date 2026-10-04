"""RC6: solid supports and a no-local-support DIMM control, one plate."""
import argparse,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import study_sparse_peel_v4_4 as study
import study_solid_support_v4_4_rc6 as solid
from build_combined_trial_v4_4_rc2 import label
from operation_marks import top_cut

ROOT=study.ROOT;v=study.v;g=study.g;full=study.full;NS=g.dual.NS
VERSION='4.4-rc6-solid-trial'

def parts():
    dense=solid.coupons(5.0)
    a=dense[0];a['name']='A';a['translation']=[45,20,0]
    a['model']-=top_cut(label('A').translate((12,30)),.6)
    n=solid.coupons(5.0)[0];n['name']='N';n['kind']='dimm_bare';n['translation']=[45,70,0]
    n['model']-=top_cut(label('N').translate((12,30)),.6)
    n['interfaces']=[];n['cores']=[];n['insert_records']=[]
    c1=dense[1];c1['translation']=[45,125,0]
    c3=dense[2];c3['translation']=[95,125,0]
    qs=[a,n,c1,c3];study.verify(qs)
    _,checks=solid.product(5.0)
    boxes=[]
    for q in qs:
        b=np.array([np.array(s.bounding_box()).reshape(2,3)+q['translation'] for s in [q['model']]+q['cores']+q['interfaces']]);lo=b[:,0].min(0);hi=b[:,1].max(0)
        for a,c in boxes:assert np.any(hi[:2]+4<a[:2]) or np.any(c[:2]+4<lo[:2])
        boxes.append((lo,hi))
    return qs,checks

def build(out):
    qs,checks=parts();old=g.dual.parts,g.dual.VERSION,g.dual.should_block
    def blocker(q,kind,role,length=0):
        if kind=='dimm_bare':return True
        return old[2](q,kind,role,length)
    try:
        g.dual.parts=lambda:qs;g.dual.VERSION=VERSION;g.dual.should_block=blocker;g.dual.build(out)
    finally:g.dual.parts,g.dual.VERSION,g.dual.should_block=old
    path=out/f'rdimm-{VERSION}-plate-0-dual.3mf'
    with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
    root=E.fromstring(data['3D/3dmodel.model']);config=E.fromstring(data['Metadata/model_settings.config'])
    resources=root.find('{'+NS+'}resources');bu=root.find('{'+NS+'}build')
    resources.remove(next(o for o in resources if o.find('{'+NS+'}components') is not None));bu.clear()
    original=config.find('object');config.remove(original)
    metadata=json.loads((out/'verification.json').read_text());rid=max(x['id'] for x in metadata['volumes'])
    for q in qs:
        rid+=1;wrapper=E.SubElement(resources,'{'+NS+'}object',id=str(rid),type='model');components=E.SubElement(wrapper,'{'+NS+'}components')
        c=E.SubElement(config,'object',id=str(rid));E.SubElement(c,'metadata',key='name',value=q['name']);E.SubElement(c,'metadata',key='extruder',value='1')
        for volume in metadata['volumes']:
            if volume['coupon']!=q['name']:continue
            oid=str(volume['id']);E.SubElement(components,'{'+NS+'}component',objectid=oid);c.append(original.find("part[@id='"+oid+"']"))
        E.SubElement(bu,'{'+NS+'}item',objectid=str(rid))
    for n,r in [('3D/3dmodel.model',root),('Metadata/model_settings.config',config)]:data[n]=E.tostring(r,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    metadata.update(scope='Solid support removal and no-local-support control; four coupons, not production parts',
        complete_product_checks=checks,coupon_checks=study.verify(qs),physical_verified=False,
        removable_unit_count=4,modeled_interface_material='Solid Bambu Support For PLA pads including grips; no PLA handles',
        comparison='A supported / N no local support; C1/C3 solid supports; all permanent structures remain PLA; grip top5.0')
    (out/'verification.json').write_text(json.dumps(metadata,indent=2));return path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/f'models/v{VERSION}');build(p.parse_args().output_dir)
