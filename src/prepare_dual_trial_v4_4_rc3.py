"""Configure P2S + AMS 2 Pro: PLA bodies, dedicated Support For PLA interfaces."""
import argparse,json,subprocess,zipfile,hashlib
from pathlib import Path
import xml.etree.ElementTree as E
from build_dual_trial_v4_4_rc3 import ROOT,VERSION
from prepare_v3_2_project import OVERRIDES
from check_bambu_v3 import read_mesh
import numpy as np

def main(bambu,profiles):
    def resolve(kind,name):
        d=json.loads((profiles/kind/(name+'.json')).read_text(encoding='utf8'));s=resolve(kind,d['inherits']) if d.get('inherits') else {}
        for inc in d.get('include',[]):s.update(resolve(kind,inc))
        s.update(d);s.pop('inherits',None);s.pop('include',None);return s
    folder=ROOT/f'build/v{VERSION}-projects/0-dual';folder.mkdir(parents=True,exist_ok=True)
    machine=resolve('machine','Bambu Lab P2S 0.4 nozzle');process=resolve('process','0.20mm Standard @BBL P2S');process.update(OVERRIDES)
    process.update({'name':'RDIMM '+VERSION,'from':'User','print_settings_id':'RDIMM '+VERSION,
        'enable_prime_tower':'1','wipe_tower_x':['205'],'wipe_tower_y':['165'],
        'support_filament':'1','support_interface_filament':'2','support_top_z_distance':'0','support_bottom_z_distance':'0',
        'support_interface_spacing':'0','support_bottom_interface_spacing':'0','independent_support_layer_height':'0',
        'flush_into_infill':'0','flush_into_objects':'0','flush_into_support':'0','support_object_skip_flush':'0',
        'flush_volumes_matrix':['0','800','800','0'],'flush_volumes_vector':['400','400','400','400'],
        'flush_multiplier':['1'],'filament_colour':['#159FB5','#EEEEEE']})
    pla=resolve('filament','Bambu PLA Basic @BBL P2S');support=resolve('filament','Bambu Support For PLA @BBL P2S')
    for d in (pla,support):d['override_process_overhang_speed']=['0']
    for name,d in [('machine',machine),('process',process),('pla',pla),('support',support)]:
        (folder/(name+'.json')).write_text(json.dumps(d),encoding='utf8')
    project=folder/f'rdimm-{VERSION}-plate-0-dual-P2S-AMS2Pro-PLA-SupportForPLA.3mf'
    original=ROOT/f'models/v{VERSION}/rdimm-{VERSION}-plate-0-dual.3mf'
    commands=[[str(bambu),'--arrange','0','--load-settings',str(folder/'machine.json')+';'+str(folder/'process.json'),
        '--load-filaments',str(folder/'pla.json')+';'+str(folder/'support.json'),'--curr-bed-type','Textured PEI Plate',
        '--export-3mf',str(project),str(original)],
        [str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
    for i,cmd in enumerate(commands):
        run=subprocess.run(cmd,cwd=folder,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/f'step-{i}.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,(i,run.returncode,run.stderr[-2000:])
    with zipfile.ZipFile(project) as z:
        settings=json.loads(z.read('Metadata/project_settings.config'));config=E.fromstring(z.read('Metadata/model_settings.config'))
        mappings={p.find("metadata[@key='name']").get('value'):p.find("metadata[@key='extruder']").get('value') for p in config.findall('.//part')}
        expected=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())
        for p in expected['volumes']:assert mappings[p['name']]==str(p['filament']),(p,mappings)
        assert settings['filament_is_support']==['0','1'] and settings['support_interface_filament']=='2'
        for k in ('flush_into_objects','flush_into_infill','flush_into_support','support_object_skip_flush'):assert settings[k]=='0',(k,settings[k])
        assert settings['enable_prime_tower']=='1'
        for n in z.namelist():
            if n.endswith(('.config','.model','.json','.xml')):
                txt=z.read(n).decode('utf8');assert 'C:\\Users\\' not in txt and 'C:/Users/' not in txt
        count=sum(1 for n in z.namelist() if n.endswith('.model') for e in E.fromstring(z.read(n)).iter() if e.get('paint_supports')=='8')
        assert count==expected['painted_faces'],(count,expected['painted_faces'])
    a,b=read_mesh(original),read_mesh(project)
    assert np.array_equal(a.faces,b.faces) and np.allclose(a.vertices,b.vertices,atol=.000011,rtol=0)
    result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
    p=result['sliced_plates'][0]
    report={'version':VERSION,'project':project.name,'estimated_seconds':p['total_predication'],'filaments':p['filaments'],
        'warnings':p['warning_message'],'painted_faces':count,'assignments':mappings,'filament_changes':p['filament_change_times'],
        'max_import_vertex_rounding_mm':float(np.max(np.abs(a.vertices-b.vertices))),
        'settings':{k:settings.get(k) for k in ('filament_settings_id','filament_type','nozzle_temperature','support_interface_filament','enable_prime_tower','flush_volumes_matrix','flush_multiplier','flush_into_objects','flush_into_infill','flush_into_support')},
        'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest(),'gcode_sha256':hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),'physical_verified':False}
    (folder.parent/'slicing-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);a=p.parse_args();main(a.bambu,a.profiles)
