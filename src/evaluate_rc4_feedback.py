"""Reproduce and correct omitted P1/P2 bore blockers in an unreleased copy.

Preserves tagged RC4 assets. Checks all six coupon bores plus the ten actual
full-product candidate bores; this does not claim physical roof quality.
"""
import argparse,hashlib,json,subprocess,zipfile
import xml.etree.ElementTree as E
import numpy as np
from build_trial_v4_4_rc4 import ROOT,VERSION
from check_bambu_v3 import CORE,PROD,transform,read_mesh
from audit_dual_trial_v4_4_rc3 import parse_materials,select
import evaluate_full_product as full

OUT=ROOT/'build/rc4-feedback'

def count_bores(paths,holes):
    results=[]
    for name,kind,x,y,z in holes:
        if kind=='side':
            p=select(paths,[x-1.5,y,x+1.5,y+5.7]);p=p[(p[:,7]==1)&(p[:,4]>z-1.5)&(p[:,4]-p[:,6]<z+1.5)]
        else:
            p=select(paths,[x-1.4,y-1.4,x+1.4,y+1.4]);p=p[(p[:,7]==1)&(p[:,4]<=5.3)]
        results.append(dict(specimen=name,kind=kind,axis_mm=[x,y,z],automatic_support_segments=len(p),support_layer_tops_mm=np.unique(p[:,4]).tolist()))
    return results

def trial_holes():
    holes=[('H32','side',150,115,6.35),('H32','bottom',160,118.175,0)]
    for name,dx in [('P1',45),('P2',115)]:
        holes.extend([(name,'side',70.104-35+dx,170,6.35),(name,'bottom',41.275-35+dx,173.175,0)])
    return holes

def paint(source,target):
    with zipfile.ZipFile(source) as z:data={n:z.read(n) for n in z.namelist()}
    cache={n:E.fromstring(b) for n,b in data.items() if n.endswith('.model')}
    config=E.fromstring(data['Metadata/model_settings.config'])
    names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in config.findall('object')}
    counts={'P1':0,'P2':0};part=dict(name='body-pin-clearance',inverse=np.eye(4).tolist(),rois=[])
    def walk(path,oid,matrix,name):
        obj=next(o for o in cache[path].iter(CORE+'object') if o.get('id')==oid)
        mesh=obj.find(CORE+'mesh')
        if mesh is None:
            for c in obj.find(CORE+'components'):
                walk(c.get(PROD+'path',path).lstrip('/'),c.get('objectid'),matrix@transform(c.get('transform')),name)
            return
        verts=np.array([[float(v.get(k)) for k in ('x','y','z')] for v in mesh.find(CORE+'vertices')])
        verts=verts@matrix[:3,:3].T+matrix[:3,3]
        dx=45 if name=='P1' else 115;verts+=np.array([35-dx,-170,0])
        for tri in mesh.find(CORE+'triangles'):
            q=verts[[int(tri.get(k)) for k in ('v1','v2','v3')]]
            if np.cross(q[1]-q[0],q[2]-q[0])[2]<-1e-8 and full.blocker(q,part,'keep'):
                assert tri.get('paint_supports') is None
                tri.set('paint_supports','8');counts[name]+=1
    for item in cache['3D/3dmodel.model'].find(CORE+'build'):
        name=names[item.get('objectid')]
        if name in counts:walk('3D/3dmodel.model',item.get('objectid'),transform(item.get('transform')),name)
    assert counts['P1']==counts['P2'] and counts['P1']>0,counts
    for n,root in cache.items():data[n]=E.tostring(root,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    a,b=read_mesh(source),read_mesh(target)
    assert np.array_equal(a.vertices,b.vertices) and np.array_equal(a.faces,b.faces)
    return counts

def main(bambu):
    OUT.mkdir(parents=True,exist_ok=True)
    original=ROOT/f'build/v{VERSION}-projects';r=json.loads((original/'slicing-report.json').read_text())
    source=original/'0-dual'/r['project'];assert hashlib.sha256(source.read_bytes()).hexdigest()==r['project_sha256']
    before_paths,_=parse_materials(original/'0-dual/plate_1.gcode');before=count_bores(before_paths,trial_holes())
    assert all(q['automatic_support_segments']>0 for q in before if q['specimen'] in ('P1','P2'))
    assert all(q['automatic_support_segments']==0 for q in before if q['specimen']=='H32')
    target=OUT/'RESEARCH-NOT-PRINT-rc4-bore-blockers.3mf';counts=paint(source,target)
    with (OUT/'slice.log').open('wb') as log:
        result=subprocess.run([bambu,'--arrange','0','--slice','0','--outputdir',str(OUT),str(target)],cwd=OUT,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,result.returncode
    result=json.loads((OUT/'result.json').read_text());assert result['return_code']==0
    p=result['sliced_plates'][0];assert not p['warning_message']
    after_paths,_=parse_materials(OUT/'plate_1.gcode');after=count_bores(after_paths,trial_holes())
    assert len(after)==6 and all(q['automatic_support_segments']==0 for q in after),after
    # The whole-product selective candidate uses the original correct selector.
    product=full.OUT/'dual-selective/1-pin-clearance'
    paths,_=parse_materials(product/'plate_1.gcode');paths[:,[0,2]]-=54.5;paths[:,[1,3]]-=20
    holes=[('full body','side',x,y,6.35) for x in full.v.SIDE_X for y in (0,full.v.W-5.7)]
    holes += [('full body','bottom',x,y,0) for x in full.v.BOTTOM_X for y in full.v.BOTTOM_Y]
    whole=count_bores(paths,holes);assert len(whole)==10 and all(q['automatic_support_segments']==0 for q in whole),whole
    report=dict(scope='RC4 feedback investigation; unreleased copied project; original release unchanged',
        before=before,after=after,complete_product=whole,added_blocker_faces=counts,geometry_and_global_settings_unchanged=True,
        before_seconds=r['estimated_seconds'],after_seconds=p['total_predication'],after_filaments=p['filaments'],warnings=p['warning_message'],
        original_project_sha256=r['project_sha256'],research_project_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        research_gcode_sha256=hashlib.sha256((OUT/'plate_1.gcode').read_bytes()).hexdigest(),
        full_product_gcode_sha256=hashlib.sha256((product/'plate_1.gcode').read_bytes()).hexdigest(),
        physical_corrected_P1_P2_roof_verified=False)
    (OUT/'bore-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',required=True);main(p.parse_args().bambu)
