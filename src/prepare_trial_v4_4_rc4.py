"""Configure and slice the six-object RC4 plate, retaining object overrides."""
import argparse,hashlib,json,subprocess,zipfile
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
from build_trial_v4_4_rc4 import ROOT,VERSION,PROCESS_OVERRIDE
from prepare_v3_2_project import OVERRIDES
from check_bambu_v3 import read_mesh

def main(bambu,profiles):
    def resolve(kind,name):
        d=json.loads((profiles/kind/(name+'.json')).read_text(encoding='utf8'));s=resolve(kind,d['inherits']) if d.get('inherits') else {}
        for inc in d.get('include',[]):s.update(resolve(kind,inc))
        s.update(d);s.pop('inherits',None);s.pop('include',None);return s
    folder=ROOT/f'build/v{VERSION}-projects/0-dual';folder.mkdir(parents=True,exist_ok=True)
    machine=resolve('machine','Bambu Lab P2S 0.4 nozzle');process=resolve('process','0.20mm Standard @BBL P2S');process.update(OVERRIDES)
    process.update(name='RDIMM '+VERSION,**{'from':'User','print_settings_id':'RDIMM '+VERSION,
        'enable_prime_tower':'1','wipe_tower_x':['205'],'wipe_tower_y':['165'],
        'support_filament':'1','support_interface_filament':'1','support_top_z_distance':'0.2','support_bottom_z_distance':'0.2',
        'support_interface_spacing':'0.25','support_bottom_interface_spacing':'0.25','independent_support_layer_height':'0',
        'flush_into_infill':'0','flush_into_objects':'0','flush_into_support':'0','support_object_skip_flush':'0',
        'flush_volumes_matrix':['0','800','800','0'],'flush_volumes_vector':['400','400','400','400'],
        'flush_multiplier':['1'],'filament_colour':['#159FB5','#EEEEEE']})
    pla=resolve('filament','Bambu PLA Basic @BBL P2S');support=resolve('filament','Bambu Support For PLA @BBL P2S')
    for d in (pla,support):d['override_process_overhang_speed']=['0']
    for name,d in [('machine',machine),('process',process),('pla',pla),('support',support)]:(folder/(name+'.json')).write_text(json.dumps(d))
    project=folder/f'rdimm-{VERSION}-plate-0-P2S-AMS2Pro.3mf';original=ROOT/f'models/v{VERSION}/rdimm-{VERSION}-plate-0-dual.3mf'
    commands=[[str(bambu),'--arrange','0','--load-settings',str(folder/'machine.json')+';'+str(folder/'process.json'),
        '--load-filaments',str(folder/'pla.json')+';'+str(folder/'support.json'),'--curr-bed-type','Textured PEI Plate','--export-3mf',str(project),str(original)],
        [str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
    for i,cmd in enumerate(commands):
        with (folder/f'step-{i}.log').open('wb') as log:r=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert r.returncode==0,(i,r.returncode)
    expected=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())
    with zipfile.ZipFile(project) as z:
        settings=json.loads(z.read('Metadata/project_settings.config'));config=E.fromstring(z.read('Metadata/model_settings.config'))
        mappings={}
        for o in config.findall('object'):
            inherited=o.find("metadata[@key='extruder']").get('value')
            for p in o.findall('part'):
                e=p.find("metadata[@key='extruder']")
                mappings[p.find("metadata[@key='name']").get('value')]=inherited if e is None else e.get('value')
        for p in expected['volumes']:assert mappings[p['name']]==str(p['filament'])
        objects={o.find("metadata[@key='name']").get('value'):{m.get('key'):m.get('value') for m in o.findall('metadata') if m.get('key')} for o in config.findall('object')}
        assert set(objects)=={'A','C1','C3','H32','P1','P2'}
        for k,val in PROCESS_OVERRIDE.items():assert objects['P2'][k]==val and k not in objects['P1'],(k,objects)
        assert settings['filament_is_support']==['0','1'] and settings['support_interface_filament']=='1'
        for k in ('flush_into_infill','flush_into_objects','flush_into_support','support_object_skip_flush'):assert settings[k]=='0'
        assert settings['enable_prime_tower']=='1' and settings['flush_volumes_matrix']==['0','800','800','0']
        count=sum(1 for n in z.namelist() if n.endswith('.model') for e in E.fromstring(z.read(n)).iter() if e.get('paint_supports')=='8')
        assert count==expected['painted_faces']
        assert not any(n.endswith('.gcode') for n in z.namelist())
        for n in z.namelist():
            if n.endswith(('.config','.model','.json','.xml')):
                txt=z.read(n).decode('utf8');assert 'C:\\Users\\' not in txt and 'C:/Users/' not in txt
    a,b=read_mesh(original),read_mesh(project)
    # Studio reorders independent objects. Match vertices to source coordinates
    # (including canonicalizing coincident part boundaries), then compare faces.
    def mapped(mesh):
        ids=[];error=0.
        for i in range(0,len(mesh.vertices),100):
            d=((mesh.vertices[i:i+100,None,:]-a.vertices[None,:,:])**2).sum(2)
            nearest=d.argmin(1);ids.extend(nearest);error=max(error,float(np.sqrt(d.min(1).max())))
        assert error<.000011,error
        return Counter(map(tuple,np.sort(np.array(ids)[mesh.faces],axis=1))),error
    aa,_=mapped(a);bb,error=mapped(b);assert aa==bb
    result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
    p=result['sliced_plates'][0];assert not p['warning_message']
    report=dict(version=VERSION,project=project.name,estimated_seconds=p['total_predication'],filaments=p['filaments'],warnings=p['warning_message'],
                filament_changes=p['filament_change_times'],painted_faces=count,assignments=mappings,object_overrides=objects,max_import_vertex_rounding_mm=error,
                settings={k:settings.get(k) for k in ('filament_settings_id','filament_is_support','support_interface_filament','support_top_z_distance','support_bottom_z_distance','support_interface_spacing','enable_prime_tower','flush_volumes_matrix','flush_into_objects','flush_into_infill','flush_into_support','internal_solid_infill_line_width','sparse_infill_line_width','infill_combination','wall_loops','top_shell_layers','bottom_shell_layers')},
                project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),physical_verified=False)
    (folder.parent/'slicing-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);a=p.parse_args();main(a.bambu,a.profiles)
