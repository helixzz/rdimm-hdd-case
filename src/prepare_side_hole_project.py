"""Create a separately versioned support-paint process patch, preserving geometry."""
import argparse
import hashlib
import json
import subprocess
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from block_side_hole_supports import paint
from check_bambu_v3 import read_mesh

ROOT=Path(__file__).resolve().parents[1]


def prepare(bambu,geometry_version,arch_windows=False,source_version=None,release_version=None):
    if arch_windows:
        assert geometry_version in ('4.1-rc2','4.2'),'Arch paint requires the verified RC2 body'
        if geometry_version=='4.2':
            import manifold3d as m
            import trimesh
            def solid(path):
                mesh=trimesh.load_mesh(path)
                return m.Manifold(m.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
            old=solid(ROOT/'models/v4.1-rc2/body-pin-clearance.stl')
            new=solid(ROOT/'models/v4.2/body-pin-clearance.stl')
            allowed=m.Manifold()
            for y in (19.7,55.1):
                allowed+=m.Manifold.cube((.64,5.22,.53)).translate((140.48,y+13.39,7.89))
            strip=m.Manifold.cube((144.,6.04,6.44)).translate((1.5,1.58,3.98))
            allowed+=strip+strip.mirror((0,1,0)).translate((0,101.6,0))
            assert ((new-old)-allowed).volume()<.001 and ((old-new)-allowed).volume()<.001,'Body changed outside internal relief/floor strips; requalify arch and hole paint'
    version=release_version or geometry_version+('-p2' if arch_windows else '-p1')
    source=ROOT/f'build/v{source_version or geometry_version}-projects'
    dest=ROOT/f'build/v{version}-projects';results=[]
    assert source!=dest,'Keep unpainted positive control separate'
    for plate in ('1-pin-clearance','2-upper-trays'):
        original=next((source/plate).glob('*P2S*.3mf'))
        out=dest/plate;out.mkdir(parents=True,exist_ok=True)
        project=out/f'rdimm-{version}-plate-{plate}-P2S-PLA-Basic.3mf'
        if plate=='2-upper-trays':
            # No side holes here: retain the already sliced source byte-for-byte.
            shutil.copy2(original,project)
            for name in ('plate_1.gcode','result.json'):
                shutil.copy2(source/plate/name,out/name)
            result=json.loads((out/'result.json').read_text())
            assert result['return_code']==0
            p=result['sliced_plates'][0]
            results.append({'plate':plate,'project':project.name,'geometry_version':geometry_version,
                'source_project_bytes_identical':True,'changed_global_settings':[],
                'estimated_seconds':p['total_predication'],'grams':p['filaments'][0]['total_used_g'],
                'warnings':p['warning_message'],'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest()})
            continue
        seed=out/'painted-input.3mf'
        counts=paint(original,seed,arch_windows=arch_windows)
        with zipfile.ZipFile(seed) as z:data={n:z.read(n) for n in z.namelist()}
        settings=json.loads(data['Metadata/project_settings.config'])
        settings['print_settings_id']='RDIMM '+version+' - six side holes support blocked'
        if arch_windows:settings['print_settings_id']+=' + two arch roofs'
        if 'name' in settings:settings['name']=settings['print_settings_id']
        data['Metadata/project_settings.config']=json.dumps(settings).encode()
        with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in data.items():z.writestr(n,b)
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
    if arch_windows:report['scope']+='; RC2 45-degree arch roofs with R1 apex also blocked (maximum apex chord 1.415 mm)'
    (dest/'slicing-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bambu',type=Path,required=True)
    p.add_argument('--geometry-version',default='4.0-rc4')
    p.add_argument('--arch-windows',action='store_true')
    p.add_argument('--source-version')
    p.add_argument('--release-version')
    a=p.parse_args();prepare(a.bambu,a.geometry_version,a.arch_windows,a.source_version,a.release_version)
