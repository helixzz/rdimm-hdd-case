"""Connected sparse Support For PLA inserts; full-product research before coupons.

No separate weak PLA-core/contact-film joint. This is nominal geometry and
toolpath research, not a prediction of removal force or material adhesion.
"""
import argparse, hashlib, json, subprocess, zipfile
from pathlib import Path
import numpy as np
import evaluate_dfm_geometry as g
import evaluate_full_product as full
from build_v4_1 import CAPTURES
from check_bambu_v3 import read_mesh

ROOT=g.ROOT; v=g.v; base=g.base
OUT=ROOT/'build/sparse-peel-study'

def fingers(start,end,gap,width=.8):
    # Keep both outermost ribs; distribute the intervening clear spaces evenly.
    n=max(2,int(np.ceil((end-start+gap)/(width+gap))))
    actual=(end-start-n*width)/(n-1)
    assert 0 < actual <= gap+1e-6
    return [(start+i*(width+actual),width) for i in range(n)],actual

def dimm_insert(moving,gap,keyed=False):
    a,b=(28.35,32.65) if moving else (14.85,22.05)
    ribs,actual=fingers(a,b,gap)
    x=6.95 if moving else 6.65
    solid=v.m.Manifold()
    for y,w in ribs:solid+=v.box((7.9-x,w,1.6),(x,y,3.0))
    # The diagonal spine joins every rib over its rising height, into the
    # accessible empty slot. 45-degree underside; no low hanging pull feet.
    pts=[(7.75,3.0),(9.55,4.8),(9.55,5.0),(8.15,5.0),(7.75,4.6)] if keyed else [(7.75,3.0),(10.0,5.25),(10.0,5.8),(8.8,5.8),(7.75,4.6)]
    solid+=base.rc.wedge(pts,a,b-a)
    handle=v.m.Manifold()
    if keyed:
        cy=(a+b)/2
        handle=v.box((.55,2.8,.6),(7.95,cy-1.4,4.0))
        handle+=base.rc.wedge([(8.25,4.0),(10.25,6.0),(10.25,6.6),(9.05,6.6),(8.25,4.6)],cy-.6,1.2)
        # Two side shoulders of the T key bear on the continuous dedicated
        # frame. The materials share boundaries but do not overlap.
        solid-=handle
    if moving:solid=solid.mirror((1,0,0)).translate((147.3,0,0))
    if moving:handle=handle.mirror((1,0,0)).translate((147.3,0,0))
    return solid.set_tolerance(.001).simplify(.001),dict(kind='moving' if moving else 'fixed',
        rib_width_mm=.8,rib_count=len(ribs),max_clear_gap_mm=actual,contact_fraction=len(ribs)*.8/(b-a),
        ribs=ribs,contact_x_mm=[139.4,140.35] if moving else [6.65,7.9],contact_z_mm=[3.,4.6]),handle

def capture_insert(length,gap,keyed=False):
    a,b=2.3,2+length-.3
    # Retain RC4's physically printed .6 mm end contacts, rather than adding
    # new middle contacts just to apply the DIMM rib pitch to this short roof.
    ribs=[(a,.6),(b-.6,.6)];actual=b-a-1.2
    solid=v.m.Manifold()
    for y,w in ribs:solid+=v.box((2.9,w,1.9),(3.4,y,2.9))
    pts=[(6.15,2.9),(8.25,5.0),(8.25,5.2),(6.7,5.2),(6.7,4.8),(6.15,4.8)] if keyed else [(6.15,2.9),(8.25,5.0),(9.0,5.0),(9.0,6.4),(6.7,6.4),(6.7,4.8),(6.15,4.8)]
    solid+=base.rc.wedge(pts,a,b-a)
    handle=v.m.Manifold()
    if keyed:
        cy=(a+b)/2
        handle=v.box((.65,2.0,.6),(6.45,cy-1,4.0))
        handle+=base.rc.wedge([(6.85,4.0),(8.85,6.0),(8.85,6.4),(7.65,6.4),(6.85,4.6)],cy-.5,1.0)
        solid-=handle
    return solid.set_tolerance(.001).simplify(.001),dict(kind='capture',rib_width_mm=.6,rib_count=len(ribs),
        max_clear_gap_mm=actual,contact_fraction=len(ribs)*.6/(b-a),ribs=ribs,contact_x_mm=[3.4,6.3],contact_z_mm=[2.9,4.8]),handle

def coupons(gap,keyed=False):
    qs=g.specimens('combined')
    for q in qs:
        q['cores']=[]; q['interfaces']=[]; q['insert_records']=[]
        if q['kind']=='dimm':
            for moving in (False,True):
                s,r,h=dimm_insert(moving,gap,keyed);q['interfaces'].append(s);q['insert_records'].append(r)
                if keyed:q['cores'].append(h)
        if q['kind']=='capture':
            s,r,h=capture_insert(q['capture_length'],gap,keyed);q['interfaces']=[s];q['insert_records']=[r]
            if keyed:q['cores']=[h]
    return qs

def verify(qs):
    checks={'single_connected_parts':0};poses=0
    for q in qs:
        allparts=[q['model']]+q['cores']+q['interfaces']
        for i,s in enumerate(allparts):
            assert v.meshof(s).is_watertight and len(s.decompose())==1,(q['name'],i,'mesh')
            checks['single_connected_parts']+=1
            for t in allparts[:i]:base.clear(s,t,(q['name'],i,'overlap'))
        for i,s in enumerate(q['interfaces']):
            handle=q['cores'][i] if q['cores'] else v.m.Manifold()
            direction=-1 if q['kind']=='dimm' and q['insert_records'][i]['kind']=='moving' else 1
            if q['cores']:
                assert (handle.translate((direction*.3,0,0))^s).volume()>.01,(q['name'],i,'missing mechanical key')
            for d in np.linspace(0,8,33):
                base.clear((s+handle).translate((direction*float(d),0,0)),q['model'],(q['name'],'insert extraction',i,d))
                poses+=1
    checks['connected_insert_extraction_poses']=poses
    return checks

def product(gap,keyed=False):
    plates,checks=full.make_parts(True,False)
    for _,items in plates:
        for q in items:
            name=q['name']
            if name.startswith('lid'):continue
            t=np.linalg.inv(q['inverse']); local_keep=q['model'].transform(np.array(q['inverse'])[:3,:])
            n=2 if name.startswith('body') else 3; z=4. if n==2 else 0.; records=[]
            def add(s,direction,record,h):
                mesh=v.meshof(s); assert mesh.is_watertight and len(s.decompose())==1
                base.clear(s,local_keep,(name,'insert overlap'))
                if keyed:
                    base.clear(h,local_keep,(name,'handle overlap'));base.clear(h,s,(name,'material overlap'))
                    assert (h.translate((direction*.3,0,0))^s).volume()>.01,(name,'missing mechanical key')
                    q['cores'].append(h.transform(t[:3,:]))
                for d in np.linspace(0,8,33):base.clear((s+h).translate((direction*float(d),0,0)),local_keep,(name,'insert path',d))
                q['interfaces'].append(s.transform(t[:3,:]));records.append(record)
            for i,sy in enumerate(v.layout(n)[2]):
                ty=base.rc.simple.clip_start(n,i,sy)
                for moving in (False,True):
                    s,r,h=dimm_insert(moving,gap,keyed);shift=(0,ty-14.5 if moving else sy-2.5,z)
                    r=dict(r,shift=list(shift));add(s.translate(shift),-1 if moving else 1,r,h.translate(shift))
                q['rois'] += [([6.29,sy+11.99,z+4.59],[7.92,sy+20.01,z+4.95]),
                              ([139.38,ty+13.59,z+4.59],[142.01,ty+18.41,z+4.95])]
            if n==2:
                for y,length in CAPTURES:
                    for right in (False,True):
                        s,r,h=capture_insert(length,gap,keyed);s=s.translate((0,y-2,19.2));h=h.translate((0,y-2,19.2))
                        if right:
                            s=s.mirror((1,0,0)).translate((147,0,0));h=h.mirror((1,0,0)).translate((147,0,0))
                        add(s,-1 if right else 1,dict(r,shift=[0,y-2,19.2],mirror=right),h)
                        q['rois'].append(([140.599 if right else 2.39,y-.001,23.189],[144.61 if right else 6.401,y+length+.001,24.001]))
            q['insert_records']=records
            row=next(x for x in checks['details'] if x['part']==name)
            row.update(cores=len(q['cores']),interfaces=len(q['interfaces']),core_extraction_poses=len(q['interfaces'])*33)
    checks['connected_insert_count']=sum(len(q['interfaces']) for _,items in plates for q in items)
    checks['insert_extraction_poses']=checks['connected_insert_count']*33
    return plates,checks

def slice_project(original,folder,bambu,tower=(12,150)):
    src=ROOT/'build/v4.4-rc4-product-trial-projects/0-dual'
    process=json.loads((src/'process.json').read_text());process['wipe_tower_x']=[str(tower[0])];process['wipe_tower_y']=[str(tower[1])]
    (folder/'process.json').write_text(json.dumps(process));project=folder/'RESEARCH-not-released.3mf'
    commands=[[bambu,'--arrange','0','--load-settings',str(src/'machine.json')+';'+str(folder/'process.json'),
        '--load-filaments',str(src/'pla.json')+';'+str(src/'support.json'),'--curr-bed-type','Textured PEI Plate','--export-3mf',str(project),str(original)],
        [bambu,'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
    for i,cmd in enumerate(commands):
        with (folder/f'step-{i}.log').open('wb') as log:
            run=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert run.returncode==0,(folder,i,run.returncode)
    a,b=read_mesh(original),read_mesh(project)
    assert np.array_equal(a.faces,b.faces) and np.allclose(a.vertices,b.vertices,atol=.000011,rtol=0)
    result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
    p=result['sliced_plates'][0];assert not p['warning_message'],p['warning_message']
    with zipfile.ZipFile(project) as archive:
        settings=json.loads(archive.read('Metadata/project_settings.config'))
        assert settings['filament_is_support']==['0','1']
        assert settings['flush_volumes_matrix']==['0','800','800','0']
    return dict(seconds=p['total_predication'],changes=p['filament_change_times'],filaments=p['filaments'],warnings=p['warning_message'],
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest())

def main(bambu,geometry_only,keyed=False,gaps=(.8,1.2,1.6)):
    OUT.mkdir(parents=True,exist_ok=True)
    for gap in gaps:
        name=('keyed-' if keyed else '')+'gap-'+str(gap);qs=coupons(gap,keyed);report=dict(coupons=verify(qs))
        plates,checks=product(gap,keyed);report['complete_geometry']=checks;report['plates']=[]
        for label,items in plates:
            folder=OUT/name/label;folder.mkdir(parents=True,exist_ok=True)
            source=full.export(items,folder,'SPARSE-STUDY-'+name+'-'+label)
            if not geometry_only:report['plates'].append(dict(plate=label,**slice_project(source,folder,bambu)))
        (OUT/(name+'.json')).write_text(json.dumps(report,indent=2));print(name,report,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu');p.add_argument('--geometry-only',action='store_true');p.add_argument('--keyed',action='store_true');p.add_argument('--gaps',nargs='+',type=float,default=[.8,1.2,1.6]);a=p.parse_args();main(a.bambu,a.geometry_only,a.keyed,a.gaps)
