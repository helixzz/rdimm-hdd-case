"""Prepare the combined trial with only the necessary local support blockers."""
import argparse,json,zipfile,subprocess,hashlib
import xml.etree.ElementTree as E
import numpy as np
from build_combined_trial_v4_4_rc2 import ROOT,VERSION
from block_side_hole_supports import CORE,PROD
from check_bambu_v3 import read_mesh

def block(q,kind):
    def roi(lo,hi):return np.all(q>=lo) and np.all(q<=hi)
    if kind=='dimm':
        return any(roi(lo,hi) for lo,hi in [([6.29,14.49,4.59],[7.92,22.51,4.95]),([139.38,28.09,4.59],[142.01,32.91,4.95]),([6.64,14.84,.79],[13.01,18.16,4.41]),([6.64,18.74,.79],[13.01,22.06,4.41]),([133.79,28.34,.79],[140.36,32.66,4.41])])
    return False

def main(bambu):
    folder=ROOT/f'build/v{VERSION}-projects/0-combined';folder.mkdir(parents=True,exist_ok=True)
    original=next((ROOT/f'build/v{VERSION}-unpainted-projects/0-combined').glob('*P2S*.3mf'))
    records=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())['specimens']
    counts={r['name']:0 for r in records};counts['bottom_roofs']=0;counts['side_roofs']=0
    with zipfile.ZipFile(original) as z:data={n:z.read(n) for n in z.namelist()}
    root=E.fromstring(data['3D/3dmodel.model']);item=root.find(f'{{{CORE}}}build/{{{CORE}}}item');comp=root.find(f'.//{{{CORE}}}component')
    t=np.array([float(x) for x in item.attrib['transform'].split()]);assert np.allclose(t[:9],[1,0,0,0,1,0,0,0,1])
    ct=np.array([float(x) for x in comp.attrib['transform'].split()]);assert np.allclose(ct,[1,0,0,0,1,0,0,0,1,0,0,0])
    path=comp.attrib[f'{{{PROD}}}path'].lstrip('/');model=E.fromstring(data[path]);verts=np.array([[float(e.attrib[k]) for k in ('x','y','z')] for e in model.findall(f'.//{{{CORE}}}vertex')])+t[9:]
    for tri in model.findall(f'.//{{{CORE}}}triangle'):
        world=verts[[int(tri.attrib[k]) for k in ('v1','v2','v3')]]
        if np.cross(world[1]-world[0],world[2]-world[0])[2]>=-1e-8:continue
        for r in records:
            q=world-r['translation'];yes=False
            if r['kind']=='dimm':yes=block(q,'dimm')
            elif r['kind']=='capture':
                length=r['capture_length']
                # Real cap undersides / root fillet and manual pad undersides.
                yes=(np.all(q>=[2.39,1.999,3.989]) and np.all(q<=[6.401,2+length+.001,4.801])) or (np.all(q>=[3.39,2.299,3.19]) and np.all(q<=[8.01,2+length-.299,6.401]))
            elif r['kind']=='mount':
                radius=r['diameter']/2
                bottom=np.allclose(q[:,2],5.3,atol=.001) and np.all(np.linalg.norm(q[:,:2]-[15,3.175],axis=1)<=radius+.001)
                side=np.all(q>=[5-radius-.311,-.001,6.35-radius-.311]) and np.all(q<=[5+radius+.311,5.701,6.35+radius+.311])
                yes=bottom or side
                if yes:counts['bottom_roofs' if bottom else 'side_roofs']+=1
            if yes:
                tri.set('paint_supports','8');counts[r['name']]+=1;break
    assert all(counts[r['name']]>0 for r in records if r['kind']!='corner'),counts
    expected=sum(counts[r['name']] for r in records)
    data[path]=E.tostring(model,encoding='utf-8',xml_declaration=True)
    seed=folder/'painted-input.3mf';project=folder/f'rdimm-{VERSION}-plate-0-combined-P2S-PLA-Basic.3mf'
    with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    for i,cmd in enumerate([[bambu,'--arrange','0','--export-3mf',str(project),str(seed)],[bambu,'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]):
        run=subprocess.run(cmd,cwd=folder,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/f'step-{i}.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,(i,run.returncode)
    before,after=read_mesh(original),read_mesh(project)
    assert np.allclose(before.vertices,after.vertices,atol=.000005) and np.array_equal(before.faces,after.faces)
    with zipfile.ZipFile(original) as za,zipfile.ZipFile(project) as zb:
        assert json.loads(za.read('Metadata/project_settings.config'))==json.loads(zb.read('Metadata/project_settings.config'))
        actual=sum(1 for n in zb.namelist() if n.endswith('.model') for e in E.fromstring(zb.read(n)).iter() if e.attrib.get('paint_supports')=='8')
        assert actual==expected,(actual,expected)
    result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
    p=result['sliced_plates'][0]
    report={'version':VERSION,'project':project.name,'painted_faces':expected,'paint_counts':counts,'mesh_and_global_settings_unchanged':True,'estimated_seconds':p['total_predication'],'grams':p['filaments'][0]['total_used_g'],'warnings':p['warning_message'],'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest(),'gcode_sha256':hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),'physical_verified':False}
    (folder.parent/'slicing-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',required=True);main(p.parse_args().bambu)
