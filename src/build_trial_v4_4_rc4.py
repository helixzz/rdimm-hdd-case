"""Six specimens on one plate, selected from full-product manufacturing studies."""
import argparse,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import evaluate_dfm_geometry as g
import evaluate_full_product as full
from build_combined_trial_v4_4_rc2 import label
from operation_marks import top_cut

ROOT=g.ROOT;v=g.v;VERSION='4.4-rc4-product-trial';NS=g.dual.NS
PROCESS_OVERRIDE={'internal_solid_infill_line_width':'0.5','sparse_infill_line_width':'0.5','infill_combination':'1'}

def parts():
    q=g.specimens('combined')
    p,_,_,checks=full.geometry(True)
    # Actual floor/side reinforcement, at the same Z and printing orientation.
    source_box=v.box((50,16,12),(35,0,0))
    section=(p['body-pin-clearance']^source_box).translate((-35,0,0)).set_tolerance(.001).simplify(.001)
    for i,x in enumerate((45,115),1):
        s=section-top_cut(label('P'+str(i)).translate((3,10)),4)
        q.append(dict(name='P'+str(i),kind='process',model=s,cores=[],interfaces=[],translation=[x,170,0],
                      source='full body-pin-clearance',source_crop=[[35,0,0],[85,16,12]],
                      process_overrides=PROCESS_OVERRIDE if i==2 else {}))
    # Labels are the only geometry difference between the two process specimens.
    keep_outside_label=v.box((50,16,12))-v.box((10,5,.5),(1,9,3.5))
    assert ((q[-1]['model']^keep_outside_label)-(q[-2]['model']^keep_outside_label)).volume()<.001
    assert ((q[-2]['model']^keep_outside_label)-(q[-1]['model']^keep_outside_label)).volume()<.001
    g.check_specimens(q)
    boxes=[]
    for part in q:
        bounds=np.array([np.array(s.bounding_box()).reshape(2,3)+part['translation'] for s in [part['model']]+part['cores']+part['interfaces']])
        lo=bounds[:,0].min(0);hi=bounds[:,1].max(0)
        for a,b in boxes:assert np.any(hi[:2]+4<a[:2]) or np.any(b[:2]+4<lo[:2]),part['name']
        boxes.append((lo,hi))
    return q,checks

def build(out):
    q,checks=parts();old=g.dual.parts,g.dual.VERSION,g.dual.should_block
    try:
        g.dual.parts=lambda:q;g.dual.VERSION=VERSION
        g.dual.should_block=lambda verts,kind,role,length=0:False if kind=='process' else old[2](verts,kind,role,length)
        g.dual.build(out)
    finally:g.dual.parts,g.dual.VERSION,g.dual.should_block=old
    path=out/f'rdimm-{VERSION}-plate-0-dual.3mf'
    with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
    root=E.fromstring(data['3D/3dmodel.model']);config=E.fromstring(data['Metadata/model_settings.config'])
    resources=root.find('{'+NS+'}resources');build=root.find('{'+NS+'}build')
    old_wrapper=next(o for o in resources if o.find('{'+NS+'}components') is not None)
    resources.remove(old_wrapper);build.clear()
    original=config.find('object');config.remove(original)
    metadata=json.loads((out/'verification.json').read_text());rid=max(x['id'] for x in metadata['volumes'])
    for part in q:
        rid+=1;wrapper=E.SubElement(resources,'{'+NS+'}object',id=str(rid),type='model')
        components=E.SubElement(wrapper,'{'+NS+'}components')
        c=E.SubElement(config,'object',id=str(rid));E.SubElement(c,'metadata',key='name',value=part['name']);E.SubElement(c,'metadata',key='extruder',value='1')
        for k,val in part.get('process_overrides',{}).items():E.SubElement(c,'metadata',key=k,value=val)
        for volume in metadata['volumes']:
            if volume['coupon']!=part['name']:continue
            oid=str(volume['id']);E.SubElement(components,'{'+NS+'}component',objectid=oid)
            c.append(original.find("part[@id='"+oid+"']"))
        E.SubElement(build,'{'+NS+'}item',objectid=str(rid))
    data['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True)
    data['Metadata/model_settings.config']=E.tostring(config,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    metadata.update(scope='Six physical verification specimens selected from full-product studies; not production parts',
                    complete_product_checks=checks,coupon_checks=g.check_specimens(q),process_comparison='P1 baseline / P2 wider internal lines + combined sparse infill; labels differ only')
    (out/'verification.json').write_text(json.dumps(metadata,indent=2));return path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/f'models/v{VERSION}');build(p.parse_args().output_dir)
