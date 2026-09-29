"""Create a separately versioned support-paint process patch, preserving geometry."""
import argparse
import hashlib
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from block_side_hole_supports import paint
from check_bambu_v3 import read_mesh

ROOT=Path(__file__).resolve().parents[1]


def prepare(bambu,geometry_version):
    version=geometry_version+'-p1'
    source=ROOT/f'build/v{geometry_version}-projects'
    dest=ROOT/f'build/v{version}-projects';results=[]
    for plate in ('1-pin-clearance','2-upper-trays'):
        original=next((source/plate).glob('*P2S*.3mf'))
        out=dest/plate;out.mkdir(parents=True,exist_ok=True)
        seed=out/'painted-input.3mf'
        if plate.startswith('1'):
            counts=paint(original,seed)
        else:
            seed.write_bytes(original.read_bytes());counts={}
        with zipfile.ZipFile(seed) as z:data={n:z.read(n) for n in z.namelist()}
        settings=json.loads(data['Metadata/project_settings.config'])
        settings['print_settings_id']='RDIMM '+version+' - six side holes support blocked'
        if 'name' in settings:settings['name']=settings['print_settings_id']
        data['Metadata/project_settings.config']=json.dumps(settings).encode()
        with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in data.items():z.writestr(n,b)
        project=out/f'rdimm-{version}-plate-{plate}-P2S-PLA-Basic.3mf'
        for i,command in enumerate([
            [str(bambu),'--arrange','0','--export-3mf',str(project),str(seed)],
            [str(bambu),'--arrange','0','--slice','0','--outputdir',str(out),str(project)]
        ]):
            run=subprocess.run(command,cwd=out,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (out/f'step-{i}.log').write_bytes(run.stdout+run.stderr)
            assert run.returncode==0,(plate,i,run.returncode)
        with zipfile.ZipFile(project) as z:
            npaint=sum(1 for n in z.namelist() if n.endswith('.model') for e in ET.fromstring(z.read(n)).iter() if e.attrib.get('paint_supports')=='8')
            assert npaint==sum(counts.values()),('paint lost during save',npaint,counts)
            newsettings=json.loads(z.read('Metadata/project_settings.config'))
        with zipfile.ZipFile(original) as z:oldsettings=json.loads(z.read('Metadata/project_settings.config'))
        changed={k for k in oldsettings.keys()|newsettings.keys() if oldsettings.get(k)!=newsettings.get(k)}
        assert changed<={'print_settings_id','name'},changed
        before,after=read_mesh(original),read_mesh(project)
        # Bambu re-save rounds some serialized coordinates by up to 0.000004 mm.
        assert before.vertices.shape==after.vertices.shape
        delta=float(np.abs(before.vertices-after.vertices).max())
        assert delta<=0.000005,delta
        assert np.array_equal(before.faces,after.faces)
        result=json.loads((out/'result.json').read_text())
        assert result['return_code']==0
        p=result['sliced_plates'][0]
        results.append({'plate':plate,'project':project.name,'geometry_version':geometry_version,
            'blocked_faces_per_hole':counts,'roundtrip_blocked_faces':npaint,'max_roundtrip_vertex_delta_mm':delta,'triangle_indices_identical':True,
            'changed_global_settings':sorted(changed),'estimated_seconds':p['total_predication'],
            'grams':p['filaments'][0]['total_used_g'],'warnings':p['warning_message'],
            'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest()})
    report={'version':version,'geometry_version':geometry_version,'scope':'Pin-clearance bodies only; upper cylindrical side-hole faces blocked; geometry unchanged',
            'results':results,'physical_hole_clearance_verified':False,
            'limits':'No support extrusion does not establish zero sagging or actual pin fit. Preserve all other supports.'}
    (dest/'slicing-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bambu',type=Path,required=True)
    p.add_argument('--geometry-version',default='4.0-rc4')
    a=p.parse_args();prepare(a.bambu,a.geometry_version)
