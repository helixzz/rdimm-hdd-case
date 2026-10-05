"""One RC5 plate: integral/split keeper comparison, captures and bore checks."""
import argparse,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import study_sparse_peel_v4_4 as study
import study_split_keeper_v4_4 as split
from build_trial_v4_4_rc4 import parts as previous_parts
from build_combined_trial_v4_4_rc2 import label
from operation_marks import top_cut

ROOT=study.ROOT;v=study.v;g=study.g;full=study.full;NS=g.dual.NS
VERSION='4.4-rc5-peel-trial'

def parts():
    dense=study.coupons(.8,True)
    a=dense[0];a['name']='A';a['translation']=[45,20,0]
    b=study.coupons(.8,True)[0];b['name']='B';b['translation']=[45,70,0]
    source=b['model']+v.box((4.4,14.,4.4),(1.9,34.9,0))
    body,keeper,leaf,rec=split.split(source,[2.5],end=45.)
    split_checks=split.verify(body,keeper,leaf,rec,'B')
    b['model']=(body-top_cut(label('B').translate((12,30)),.6)).set_tolerance(.001).simplify(.001)
    for key in ('cores','interfaces','insert_records'):b[key]=b[key][1:]
    b['split_keeper']=dict(rec,checks=split_checks)
    keeper=keeper.rotate((180,0,0));lo=np.array(keeper.bounding_box()[:3]);keeper=keeper.translate(-lo)
    k=dict(name='B-KEEPER',kind='keeper',model=keeper,cores=[],interfaces=[],translation=[205,70,0])
    c1=dense[1];c1['translation']=[45,125,0]
    c3=dense[2];c3['translation']=[95,125,0]
    h=dense[3];h['translation']=[145,125,0]
    old,checks=previous_parts();p=old[-2];p['translation']=[45,170,0]
    qs=[a,b,k,c1,c3,h,p];study.verify(qs)
    boxes=[]
    for q in qs:
        b=np.array([np.array(s.bounding_box()).reshape(2,3)+q['translation'] for s in [q['model']]+q['cores']+q['interfaces']]);lo=b[:,0].min(0);hi=b[:,1].max(0)
        for a,c in boxes:assert np.any(hi[:2]+4<a[:2]) or np.any(c[:2]+4<lo[:2])
        boxes.append((lo,hi))
    return qs,checks

def build(out):
    qs,checks=parts();_,split_checks=split.full_geometry();old=g.dual.parts,g.dual.VERSION,g.dual.should_block
    def blocker(q,kind,role,length=0):
        if kind=='process':
            p=dict(name='body-pin-clearance',inverse=np.eye(4).tolist(),rois=[])
            return full.blocker(q+np.array([35,0,0]),p,role)
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
    metadata.update(scope='Two structural directions on one plate; A integral and B split keeper, plus captures and bore witnesses; not production parts',
        complete_product_checks=checks,split_product_checks=split_checks,coupon_checks=study.verify(qs),physical_verified=False,
        removable_unit_count=5,modeled_interface_material='Connected Bambu Support For PLA comb, mechanically captured PLA handle',
        comparison='A integral / B separate fixed keeper; DIMM rib gap <=.8 mm; C retains .6 mm end contacts; H32 unchanged; P1 corrected hole blockers')
    (out/'verification.json').write_text(json.dumps(metadata,indent=2));return path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/f'models/v{VERSION}');build(p.parse_args().output_dir)
