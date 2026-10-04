"""Slice the unreleased capture pull-pad study against the unchanged full plate."""
import argparse,hashlib,json,subprocess,zipfile
import xml.etree.ElementTree as E
import numpy as np
from evaluate_capture_pull_supports import parts,d,v,CAPTURES
from block_side_hole_supports import CORE,PROD
from check_bambu_v3 import read_mesh
from audit_support_trial_v4_4 import surface_gap
from audit_v3_2_toolpaths import parse,select

def main(bambu):
    root=d.base.ROOT;out=root/'build/capture-support-assessment';out.mkdir(exist_ok=True)
    source=next((root/'build/v4.3-projects/1-pin-clearance').glob('*P2S*.3mf'))
    body,pieces,_=parts()
    with zipfile.ZipFile(source) as z:data={n:z.read(n) for n in z.namelist()}
    top=E.fromstring(data['3D/3dmodel.model']);item=top.find(f'{{{CORE}}}build/{{{CORE}}}item');component=top.find(f'.//{{{CORE}}}component')
    t=np.array([float(x) for x in item.attrib['transform'].split()]);assert np.allclose(t[:9],[1,0,0,0,1,0,0,0,1])
    ct=np.array([float(x) for x in component.attrib['transform'].split()]);assert np.allclose(ct,[1,0,0,0,1,0,0,0,1,0,0,0])
    path=component.attrib[f'{{{PROD}}}path'].lstrip('/');model=E.fromstring(data[path])
    verts=model.find(f'.//{{{CORE}}}vertices');tris=model.find(f'.//{{{CORE}}}triangles')
    xyz=np.array([[float(q.attrib[k]) for k in ('x','y','z')] for q in verts])+t[9:]-[54.5,20,0]
    count=0
    for tri in tris:
        q=xyz[[int(tri.attrib[k]) for k in ('v1','v2','v3')]]
        if np.cross(q[1]-q[0],q[2]-q[0])[2]>=-1e-8:continue
        for y,length in CAPTURES:
            if np.all(q[:,1]>=y-.001) and np.all(q[:,1]<=y+length+.001) and np.all(q[:,2]>=23.19) and np.all(q[:,2]<=24.001):
                if np.all((q[:,0]>=2.39)&(q[:,0]<=6.401)) or np.all((q[:,0]>=140.599)&(q[:,0]<=144.61)):
                    tri.set('paint_supports','8');count+=1;break
    assert count>8,count
    for piece in pieces:
        mesh=v.meshof(piece);offset=len(verts)
        for q in mesh.vertices+[54.5,20,0]-t[9:]:E.SubElement(verts,f'{{{CORE}}}vertex',{k:repr(float(val)) for k,val in zip(('x','y','z'),q)})
        for face in mesh.faces:
            attr={k:str(int(i)+offset) for k,i in zip(('v1','v2','v3'),face)}
            q=mesh.vertices[face]
            if np.cross(q[1]-q[0],q[2]-q[0])[2]<-1e-8:attr['paint_supports']='8'
            E.SubElement(tris,f'{{{CORE}}}triangle',attr)
    data[path]=E.tostring(model,encoding='utf-8',xml_declaration=True)
    seed=out/'input.3mf';project=out/'capture-pad-study-NOT-RELEASED.3mf'
    with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    for i,cmd in enumerate([[bambu,'--arrange','0','--export-3mf',str(project),str(seed)],[bambu,'--arrange','0','--slice','0','--outputdir',str(out),str(project)]]):
        r=subprocess.run(cmd,cwd=out,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (out/f'step-{i}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.returncode
    a,b=read_mesh(seed),read_mesh(project);assert np.allclose(a.vertices,b.vertices,atol=.000005) and np.array_equal(a.faces,b.faces)
    with zipfile.ZipFile(source) as za,zipfile.ZipFile(project) as zb:
        assert json.loads(za.read('Metadata/project_settings.config'))==json.loads(zb.read('Metadata/project_settings.config'))
    segs=parse(out/'plate_1.gcode');checks=[]
    for y,length in CAPTURES:
        for right in (False,True):
            for yy in (y+.3,y+length-.9):
                rect=np.array([3.8,yy+.1,5.8,yy+.5])
                if right:rect[[0,2]]=147-rect[[2,0]]
                rect += [54.5,20,54.5,20]
                for split in (22.3,23.9):
                    gap=surface_gap(segs,rect,split);assert gap>=.19,(y,right,split,gap)
                    checks.append({'y':y,'right':right,'runner_y':yy,'split_z':split,'nominal_gap_mm':gap})
            rect=np.array([3.3,y+.1,6.4,y+length-.1])
            if right:rect[[0,2]]=147-rect[[2,0]]
            rect += [54.5,20,54.5,20]
            ss=select(segs,rect);ss=ss[(ss[:,7]==1)&(ss[:,4]>22.21)&(ss[:,4]-ss[:,6]<23.99)]
            assert not len(ss),('duplicated automatic support',y,right,len(ss))
    result=json.loads((out/'result.json').read_text());assert result['return_code']==0
    result=result['sliced_plates'][0]
    report={'status':'unreleased slicing study; physical removability unknown','capture_roof_faces_blocked':count,'nominal_runner_gaps':checks,'duplicated_automatic_capture_support':False,'global_settings_unchanged':True,'geometry_resave_matches_seed':True,'seconds':result['total_predication'],'grams':result['filaments'][0]['total_used_g'],'warnings':result['warning_message'],'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest(),'gcode_sha256':hashlib.sha256((out/'plate_1.gcode').read_bytes()).hexdigest(),'limits':'Whole plate estimate only. Pad neck strength, removal, flange sag and final lid fit need printing. No full release validation.'}
    (out/'slicing-assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',required=True);main(p.parse_args().bambu)
