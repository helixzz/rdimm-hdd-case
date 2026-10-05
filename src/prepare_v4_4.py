"""Configure, slice and audit the complete two-plate v4.4 P2S/AMS project."""
import argparse,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
from build_v4_4 import ROOT,VERSION,parts
from prepare_v3_2_project import OVERRIDES
from check_bambu_v3 import read_mesh
from audit_solid_support_v4_4_rc6 import audit

def main(bambu,profiles,version=VERSION,part_factory=parts):
    VERSION=version;parts=part_factory
    def resolve(kind,name):
        d=json.loads((profiles/kind/(name+'.json')).read_text(encoding='utf8'))
        s=resolve(kind,d['inherits']) if d.get('inherits') else {}
        for inc in d.get('include',[]):s.update(resolve(kind,inc))
        s.update(d);s.pop('inherits',None);s.pop('include',None);return s
    machine=resolve('machine','Bambu Lab P2S 0.4 nozzle')
    process=resolve('process','0.20mm Standard @BBL P2S');process.update(OVERRIDES)
    process.update(name=f'RDIMM v{VERSION} solid supports',**{'from':'User','print_settings_id':f'RDIMM v{VERSION} solid supports',
        'enable_prime_tower':'1','wipe_tower_x':['12'],'wipe_tower_y':['150'],
        'support_filament':'1','support_interface_filament':'1','support_top_z_distance':'0.2','support_bottom_z_distance':'0.2',
        'support_interface_spacing':'0.25','support_bottom_interface_spacing':'0.25','independent_support_layer_height':'0',
        'flush_into_infill':'0','flush_into_objects':'0','flush_into_support':'0','support_object_skip_flush':'0',
        'flush_volumes_matrix':['0','800','800','0'],'flush_volumes_vector':['400','400','400','400'],
        'flush_multiplier':['1'],'filament_colour':['#159FB5','#EEEEEE'],
        'internal_solid_infill_line_width':'0.42','sparse_infill_line_width':'0.45','infill_combination':'0'})
    pla=resolve('filament','Bambu PLA Basic @BBL P2S');support=resolve('filament','Bambu Support For PLA @BBL P2S')
    for d in (pla,support):d['override_process_overhang_speed']=['0']
    out=ROOT/f'build/v{VERSION}-projects';out.mkdir(parents=True,exist_ok=True);rows=[];audits=[]
    plates,_=parts()
    for label,items in plates:
        folder=out/label;folder.mkdir(parents=True,exist_ok=True)
        for name,d in [('machine',machine),('process',process),('pla',pla),('support',support)]:
            (folder/(name+'.json')).write_text(json.dumps(d))
        source=ROOT/f'models/v{VERSION}'/label
        original=source/f'rdimm-{VERSION}-plate-{label}.3mf'
        project=folder/f'rdimm-{VERSION}-plate-{label}-P2S-AMS2Pro.3mf'
        shutil.copyfile(source/'verification.json',folder/'verification.json')
        commands=[[str(bambu),'--arrange','0','--load-settings',str(folder/'machine.json')+';'+str(folder/'process.json'),
                   '--load-filaments',str(folder/'pla.json')+';'+str(folder/'support.json'),'--curr-bed-type','Textured PEI Plate',
                   '--export-3mf',str(project),str(original)],
                  [str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
        for i,cmd in enumerate(commands):
            with (folder/f'step-{i}.log').open('wb') as log:
                run=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            assert run.returncode==0,(label,i,run.returncode)
        a,b=read_mesh(original),read_mesh(project)
        assert np.array_equal(a.faces,b.faces) and np.allclose(a.vertices,b.vertices,atol=.000011,rtol=0)
        expected=json.loads((folder/'verification.json').read_text())
        with zipfile.ZipFile(project) as z:
            settings=json.loads(z.read('Metadata/project_settings.config'))
            config=E.fromstring(z.read('Metadata/model_settings.config'))
            assert settings['filament_settings_id']==['Bambu PLA Basic @BBL P2S','Bambu Support For PLA @BBL P2S']
            assert settings['filament_is_support']==['0','1'] and settings['support_interface_filament']=='1'
            assert settings['flush_volumes_matrix']==['0','800','800','0'] and settings['enable_prime_tower']=='1'
            for k in ('flush_into_infill','flush_into_objects','flush_into_support','support_object_skip_flush'):assert settings[k]=='0'
            mapping={}
            for obj in config.findall('object'):
                inherited=obj.find("metadata[@key='extruder']").get('value')
                for part in obj.findall('part'):
                    meta={m.get('key'):m.get('value') for m in part.findall('metadata')}
                    mapping[meta['name']]=meta.get('extruder',inherited)
                    if '-interface-' in meta['name']:assert meta['sparse_infill_density']=='100%'
            for q in expected['volumes']:assert mapping[q['name']]==str(q['filament'])
            count=sum(1 for n in z.namelist() if n.endswith('.model') for e in E.fromstring(z.read(n)).iter() if e.get('paint_supports')=='8')
            assert count==expected['painted_faces']
            assert not any(n.endswith('.gcode') for n in z.namelist())
            for n in z.namelist():
                if n.endswith(('.config','.model','.json','.xml')):
                    text=z.read(n).decode('utf8');assert 'C:/Users/' not in text and 'C:\\Users\\' not in text
        result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
        p=result['sliced_plates'][0];assert not p['warning_message']
        row=dict(plate=label,project=project.name,seconds=p['total_predication'],changes=p['filament_change_times'],
                 filaments=p['filaments'],warnings=p['warning_message'],painted_faces=count,assignments=mapping,
                 project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest())
        check=audit(items,folder);assert check['gcode_sha256']==row['gcode_sha256'];check.update(plate=label,project_sha256=row['project_sha256'])
        rows.append(row);audits.append(check);print(label,row['seconds'],row['changes'],flush=True)
    assert sum(len(c['inserts']) for c in audits)==20
    assert sum(len(c['whole_plate']['mount_holes_without_support']) for c in audits)==10
    assert sum(len(c['whole_plate']['free_clip_corridors']) for c in audits)==8
    (out/'slicing-report.json').write_text(json.dumps(dict(version=VERSION,results=rows,physical_complete_set_verified=False),indent=2))
    (out/'toolpath-audit.json').write_text(json.dumps(dict(version=VERSION,plates=audits,physical_complete_set_verified=False),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True)
    a=p.parse_args();main(a.bambu,a.profiles)
