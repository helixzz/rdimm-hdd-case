"""One dual-material trial: native-volume interface assignments, not color painting."""
import argparse,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import build_support_trial_v4_4 as ab
import build_combined_trial_v4_4_rc2 as prev
from prepare_combined_trial_v4_4_rc2 import block

ROOT=ab.ROOT;v=ab.v
VERSION='4.4-rc3-dual-trial'
MOUNT_DIAMETER=3.2
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'

def parts():
    source,_=prev.parts();lookup={q['name']:q for q in source};out=[]
    def add(name,kind,model,cores,interfaces,t,**more):
        cores=[s.set_tolerance(.001).simplify(.001) for s in cores]
        for obj in [model]+cores+interfaces:
            mesh=v.meshof(obj);assert mesh.is_watertight and mesh.is_winding_consistent,(name,obj.volume())
            assert len(obj.decompose())==1,(name,'disconnected part')
        for i,core in enumerate(cores):
            for dist in np.linspace(0,8,33):
                dx=-dist if kind=='dimm' and i==2 else dist
                ab.design.base.clear(model,core.translate((float(dx),0,0)),(name,'core removal',i,dist))
        for i,a in enumerate(cores+interfaces):
            ab.design.base.clear(model,a,(name,'permanent overlap',i))
            for b in (cores+interfaces)[i+1:]:ab.design.base.clear(a,b,(name,'material overlap',i))
        out.append(dict(name=name,kind=kind,model=model,cores=cores,interfaces=interfaces,translation=t,**more))
    q=lookup['A'];interfaces=[];cores=[]
    for i,s in enumerate(q['supports']):
        y=14.85 if i==0 else 18.75 if i==1 else 28.35
        w=3.3 if i<2 else 4.3;x=6.65 if i<2 else 139.4;dx=1.25 if i<2 else .95
        caps=[v.box((dx,w,.4),(x,y,3.0)),v.box((dx,w,.4),(x,y,4.2)),
              v.box((4.7,w,.4),(8.3 if i<2 else 133.8,y,.6))]
        for cap in caps:s-=cap
        cores.append(s);interfaces+=caps
    add('A','dimm',q['model'],cores,interfaces,[45,45,0])
    for name,t in [('C1',[45,115,0]),('C3',[95,115,0])]:
        q=lookup[name];length=q['capture_length']
        s=v.box((2.9,length-.6,.6),(3.4,2.3,3.6))
        for yy in (2.3,2+length-.9):s+=v.box((2.9,.6,1.4),(3.4,yy,3.2))
        # Grow a wider grip from the existing pad; the underside retains its
        # 45-degree rise. Root width 2.4 -> 4.8 / 3.4; inner neck x6.8 ->6.7.
        pts=[(6.2,3.2),(8.,5.),(9.,5.),(9.,6.4),(6.7,6.4),(6.7,4.6),(6.2,4.6)]
        width=4.8 if length==6 else 3.4
        s+=ab.design.m.CrossSection([pts]).extrude(width).rotate((90,0,0)).translate((0,2+length/2+width/2,0))
        caps=[]
        for yy in (2.3,2+length-.9):
            caps += [v.box((2.9,.6,.5),(3.4,yy,2.9)),v.box((2.9,.6,.4),(3.4,yy,4.4))]
        for cap in caps:s-=cap
        add(name,'capture',q['model'],[s],caps,t,capture_length=length,grip_width=width)
    h=prev.hole_coupon(MOUNT_DIAMETER,'H32');add('H32','mount',h,[],[],[145,115,0],diameter=MOUNT_DIAMETER)
    return out

def should_block(q,kind,role,length=0):
    if role!='keep':return True
    if kind=='dimm':return block(q,kind)
    if kind=='capture':return np.all(q>=[2.39,1.999,3.989]) and np.all(q<=[6.401,2+length+.001,4.801])
    if kind=='mount':return True
    return False

def build(out,plate_xy_limits=(5.,245.)):
    out.mkdir(parents=True,exist_ok=True);specimens=parts();records=[];rid=0
    E.register_namespace('',NS)
    root=E.Element('{'+NS+'}model',unit='millimeter');E.SubElement(root,'{'+NS+'}metadata',name='Application').text='BambuStudio'
    E.SubElement(root,'{'+NS+'}metadata',name='Title').text='RDIMM '+VERSION
    resources=E.SubElement(root,'{'+NS+'}resources');config=E.Element('config');entries=[];bounds=[];painted=0
    for q in specimens:
        for role,objects,filament in [('keep',[q['model']],1),('core',q['cores'],1),('interface',q['interfaces'],2)]:
            for i,s in enumerate(objects):
                rid+=1;mesh=v.meshof(s);obj=E.SubElement(resources,'{'+NS+'}object',id=str(rid),type='model')
                name=f'{q["name"]}-{role}-{i+1}';me=E.SubElement(obj,'{'+NS+'}mesh');ve=E.SubElement(me,'{'+NS+'}vertices');te=E.SubElement(me,'{'+NS+'}triangles')
                for vertex in mesh.vertices+q['translation']:E.SubElement(ve,'{'+NS+'}vertex',**dict(zip(('x','y','z'),map(str,vertex))))
                count=0
                for face in mesh.faces:
                    a=mesh.vertices[face];attrs=dict(zip(('v1','v2','v3'),map(str,face)))
                    if np.cross(a[1]-a[0],a[2]-a[0])[2]<-1e-8 and should_block(a,q['kind'],role,q.get('capture_length',0)):
                        attrs['paint_supports']='8';count+=1
                    E.SubElement(te,'{'+NS+'}triangle',**attrs)
                painted+=count
                b=mesh.bounds+q['translation'];bounds.append(b)
                record={'id':rid,'name':name,'coupon':q['name'],'role':role,'filament':filament,'bounds':b.tolist(),'volume_mm3':s.volume(),'painted_faces':count}
                entries.append(record)
        records.append({k:val for k,val in q.items() if k not in ('model','cores','interfaces')})
    wrapper=rid+1;obj=E.SubElement(resources,'{'+NS+'}object',id=str(wrapper),type='model');cs=E.SubElement(obj,'{'+NS+'}components')
    conf=E.SubElement(config,'object',id=str(wrapper));E.SubElement(conf,'metadata',key='name',value='RDIMM '+VERSION);E.SubElement(conf,'metadata',key='extruder',value='1')
    for rec in entries:
        E.SubElement(cs,'{'+NS+'}component',objectid=str(rec['id']))
        p=E.SubElement(conf,'part',id=str(rec['id']),subtype='normal_part')
        E.SubElement(p,'metadata',key='name',value=rec['name']);E.SubElement(p,'metadata',key='extruder',value=str(rec['filament']))
        if rec['role']!='keep':
            E.SubElement(p,'metadata',key='sparse_infill_density',value='100%')
            E.SubElement(p,'metadata',key='sparse_infill_pattern',value='rectilinear')
    bu=E.SubElement(root,'{'+NS+'}build');E.SubElement(bu,'{'+NS+'}item',objectid=str(wrapper))
    path=out/f'rdimm-{VERSION}-plate-0-dual.3mf'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',E.tostring(root,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/model_settings.config',E.tostring(config,encoding='utf-8',xml_declaration=True))
    bb=np.array(bounds);lo=bb[:,0].min(0);hi=bb[:,1].max(0);assert np.all(lo>=[plate_xy_limits[0],plate_xy_limits[0],-.001]) and np.all(hi<=[plate_xy_limits[1],plate_xy_limits[1],26])
    (out/'verification.json').write_text(json.dumps(dict(version=VERSION,specimens=records,volumes=entries,painted_faces=painted,plate_bounds=[lo.tolist(),hi.tolist()],selected_mount_diameter_mm=MOUNT_DIAMETER,modeled_interface_material='Bambu Support For PLA',physical_verified=False,scope='four coupons; not a complete production enclosure'),indent=2))
    print(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/f'models/v{VERSION}');build(p.parse_args().output_dir)
