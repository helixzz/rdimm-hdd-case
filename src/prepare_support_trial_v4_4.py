"""Paint only custom pull-support/roof regions; retain automatic paddle support."""
import argparse,json,zipfile,subprocess,hashlib
import xml.etree.ElementTree as ET
import numpy as np
from build_support_trial_v4_4 import ROOT,VERSION
from block_side_hole_supports import CORE,PROD
from check_bambu_v3 import read_mesh


def main(bambu):
    folder=ROOT/f'build/v{VERSION}-projects/0-support-ab';folder.mkdir(parents=True,exist_ok=True)
    original=next((ROOT/f'build/v{VERSION}-unpainted-projects/0-support-ab').glob('*P2S*.3mf'))
    with zipfile.ZipFile(original) as z:data={n:z.read(n) for n in z.namelist()}
    root=ET.fromstring(data['3D/3dmodel.model']);item=root.find(f'{{{CORE}}}build/{{{CORE}}}item');comp=root.find(f'.//{{{CORE}}}component')
    t=np.array([float(x) for x in item.attrib['transform'].split()]);assert np.allclose(t[:9],[1,0,0,0,1,0,0,0,1])
    ct=np.array([float(x) for x in comp.attrib['transform'].split()]);assert np.allclose(ct,[1,0,0,0,1,0,0,0,1,0,0,0])
    path=comp.attrib[f'{{{PROD}}}path'].lstrip('/');model=ET.fromstring(data[path])
    verts=np.array([[float(e.attrib[k]) for k in ('x','y','z')] for e in model.findall(f'.//{{{CORE}}}vertex')])+t[9:]
    count=0
    for tri in model.findall(f'.//{{{CORE}}}triangle'):
        q0=verts[[int(tri.attrib[k]) for k in ('v1','v2','v3')]]
        if np.cross(q0[1]-q0[0],q0[2]-q0[0])[2]>=-1e-8:continue
        for dy in (25.,80.):
            q=q0-[54.5,dy,0]
            rois=[([6.29,14.49,4.59],[7.92,22.51,4.95]),
                  ([139.38,28.09,4.59],[142.01,32.91,4.95]),
                  ([6.64,14.84,.79],[13.01,18.16,4.41]),
                  ([6.64,18.74,.79],[13.01,22.06,4.41]),
                  ([133.79,28.34,.79],[140.36,32.66,4.41])]
            if any(np.all(q>=lo) and np.all(q<=hi) for lo,hi in rois):
                tri.set('paint_supports','8');count+=1;break
    assert count>20
    data[path]=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    seed=folder/'painted-input.3mf';project=folder/f'rdimm-{VERSION}-plate-0-support-ab-P2S-PLA-Basic.3mf'
    with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    for i,cmd in enumerate([[str(bambu),'--arrange','0','--export-3mf',str(project),str(seed)],
                           [str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]):
        run=subprocess.run(cmd,cwd=folder,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/f'step-{i}.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,(i,run.returncode)
    before,after=read_mesh(original),read_mesh(project)
    assert np.allclose(before.vertices,after.vertices,atol=.000005) and np.array_equal(before.faces,after.faces)
    with zipfile.ZipFile(project) as z:
        actual=sum(1 for n in z.namelist() if n.endswith('.model') for e in ET.fromstring(z.read(n)).iter() if e.attrib.get('paint_supports')=='8')
        assert actual==count
    result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
    p=result['sliced_plates'][0]
    report={'version':VERSION,'project':project.name,'painted_faces':count,'mesh_unchanged':True,
        'estimated_seconds':p['total_predication'],'grams':p['filaments'][0]['total_used_g'],'warnings':p['warning_message'],
        'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest(),'gcode_sha256':hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),
        'limits':'Manual sacrificial pieces are model extrusions in preview; physical release force is unknown.'}
    (folder.parent/'slicing-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',required=True);main(p.parse_args().bambu)
