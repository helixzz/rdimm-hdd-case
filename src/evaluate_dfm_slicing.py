"""Controlled manufacturing study. Never modifies a released project or profile."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import evaluate_dfm_geometry as g
from check_bambu_v3 import read_mesh
from audit_dual_trial_v4_4_rc3 import parse_materials

def main(bambu):
    source=g.ROOT/'build/v4.4-rc3-dual-trial-projects/0-dual'
    rows=[]
    for name in ('published-rc3','paddle','raised-grips','combined'):
        folder=source if name=='published-rc3' else g.OUT/name
        folder.mkdir(parents=True,exist_ok=True)
        if name!='published-rc3':
            parts=g.specimens(name);g.check_specimens(parts)
            old_parts,old_version=g.dual.parts,g.dual.VERSION
            try:
                g.dual.parts=lambda:parts;g.dual.VERSION='DFM-STUDY-'+name
                g.dual.build(folder)
            finally:g.dual.parts,g.dual.VERSION=old_parts,old_version
            original=next(folder.glob('rdimm-*.3mf'));project=folder/'EXPERIMENT-not-released.3mf'
            cmds=[[str(bambu),'--arrange','0','--load-settings',str(source/'machine.json')+';'+str(source/'process.json'),
                '--load-filaments',str(source/'pla.json')+';'+str(source/'support.json'),'--curr-bed-type','Textured PEI Plate',
                '--export-3mf',str(project),str(original)],
                [str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
            for i,cmd in enumerate(cmds):
                run=subprocess.run(cmd,cwd=folder,capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/f'step-{i}.log').write_bytes(run.stdout+run.stderr)
                assert run.returncode==0,(name,i,run.returncode)
            a,b=read_mesh(original),read_mesh(project)
            assert np.array_equal(a.faces,b.faces) and np.allclose(a.vertices,b.vertices,atol=.000011,rtol=0)
            with zipfile.ZipFile(project) as z:
                settings=json.loads(z.read('Metadata/project_settings.config'))
                config=E.fromstring(z.read('Metadata/model_settings.config'))
                mapping={p.find("metadata[@key='name']").get('value'):p.find("metadata[@key='extruder']").get('value') for p in config.findall('.//part')}
                for p in json.loads((folder/'verification.json').read_text())['volumes']:assert mapping[p['name']]==str(p['filament'])
                assert settings['flush_volumes_matrix']==['0','800','800','0']
                for key in ('flush_into_objects','flush_into_infill','flush_into_support'):assert settings[key]=='0'
        else:project=next(folder.glob('*.3mf'))
        result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
        p=result['sliced_plates'][0]
        row=dict(name=name,estimated_seconds=p['total_predication'],filament_changes=p['filament_change_times'],
                 filaments=p['filaments'],warnings=p['warning_message'],feature_seconds=p['feature_type_times'],
                 project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
                 gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest())
        paths,features=parse_materials(folder/'plate_1.gcode')
        # A local exterior paddle. Include bead radius when testing XY overlap.
        lo=np.minimum(paths[:,:2],paths[:,2:4])-paths[:,5:6]/2
        hi=np.maximum(paths[:,:2],paths[:,2:4])+paths[:,5:6]/2
        hit=(paths[:,7]==1)&(hi[:,0]>188.25)&(lo[:,0]<189.3)&(hi[:,1]>73.2)&(lo[:,1]<78)&(paths[:,4]<=5.6)
        row['paddle_auto_support_layers_mm']=sorted(set(paths[hit,4]))
        row['support_material_print_layers_mm']=sorted(set(paths[paths[:,8]==1,4]))
        rows.append(row);print(json.dumps(row),flush=True)
    report=dict(scope='Four-coupon comparison, not whole enclosure timing',physical_verified=False,
                settings_unchanged=True,purge_each_direction_mm3=800,comparisons=rows)
    (g.OUT/'slicing.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',type=Path,required=True);main(p.parse_args().bambu)
