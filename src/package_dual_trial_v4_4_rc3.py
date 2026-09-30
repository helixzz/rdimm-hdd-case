"""Package the dual-material trial from a clean, immutable source tag."""
import hashlib
import json
import subprocess
import zipfile
from build_dual_trial_v4_4_rc3 import ROOT, VERSION


def main():
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tag='v'+VERSION
    assert commit==subprocess.check_output(['git','rev-parse',tag+'^{commit}'],cwd=ROOT,text=True).strip()
    folder=ROOT/f'build/v{VERSION}-projects'
    report=json.loads((folder/'slicing-report.json').read_text())
    audit=json.loads((folder/'toolpath-audit.json').read_text())
    project=folder/'0-dual'/report['project']
    assert hashlib.sha256(project.read_bytes()).hexdigest()==report['project_sha256']
    assert hashlib.sha256((project.parent/'plate_1.gcode').read_bytes()).hexdigest()==report['gcode_sha256']==audit['gcode_sha256']
    assert len(audit['modeled_interfaces'])==17
    assert report['settings']['filament_settings_id']==['Bambu PLA Basic @BBL P2S','Bambu Support For PLA @BBL P2S']
    with zipfile.ZipFile(project) as z:
        assert z.testzip() is None
        assert not any(n.endswith('.gcode') for n in z.namelist())
        for n in z.namelist():
            if n.endswith(('.config','.model','.json','.xml')):
                value=z.read(n).decode('utf8')
                assert 'C:\\Users\\' not in value and 'C:/Users/' not in value
    files={project.name:project.read_bytes()}
    models=ROOT/f'models/v{VERSION}'
    for name in ('verification.json','support-removal.png','plate-guide.png'):
        files[name]=(models/name).read_bytes()
    files['README.zh-CN.md']=(ROOT/f'docs/v{VERSION}.zh-CN.md').read_text(encoding='utf8').replace(f'../models/v{VERSION}/','').encode('utf8')
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    for kind,name in [('slicing','slicing-report.json'),('toolpath','toolpath-audit.json')]:
        public=ROOT/f'docs/reports/v{VERSION}-{kind}.json'
        assert public.read_bytes()==(folder/name).read_bytes()
        files['reports/'+public.name]=public.read_bytes()
    files['manifest.json']=json.dumps({'version':VERSION,'release_tag':tag,'source_commit':commit,
        'scope':'4 specimens: A DIMM slot, C1/C3 lid captures, H32 holes; NOT production parts',
        'plates':1,'printer':'P2S / 0.4 mm','ams':'AMS 2 Pro','layer_height_mm':.2,
        'logical_filaments':{'1':'Bambu PLA Basic / GFA00','2':'Bambu Support For PLA / GFS02'},
        'map_logical_filaments_to_actual_AMS_slots':True,'open_as_project':True,
        'permanent_specimens':4,'removable_PLA_cores':5,'modeled_support_material_interfaces':17,
        'selected_future_mount_diameter_mm':3.2,'automatic_paddle_support_required':True,
        'prime_tower_required':True,'do_not_delete_modeled_supports_or_interfaces':True,
        'physical_removal_and_retention_verified':False,'current_complete_release':'v4.3',
        'gcode_included':False},indent=2).encode()
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in files.items()).encode()
    out=ROOT/f'build/rdimm-v{VERSION}-P2S-AMS2Pro.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if n.endswith('.3mf')])==1
        assert not any(n.endswith(('.stl','.gcode')) for n in z.namelist())
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h
    out.with_suffix('.zip.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
    print(out)


if __name__=='__main__':main()
