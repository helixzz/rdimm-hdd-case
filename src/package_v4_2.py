"""Build the complete v4.2 release archive from a clean, tagged commit."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tag_commit=subprocess.check_output(['git','rev-parse','v4.2^{commit}'],cwd=ROOT,text=True).strip()
    assert commit==tag_commit
    folder=ROOT/'build/v4.2-projects'
    report=json.loads((folder/'slicing-report.json').read_text())
    audit=json.loads((folder/'finite-width-audit.json').read_text())
    files={}
    for row in report['results']:
        project=folder/row['plate']/row['project']
        digest=hashlib.sha256(project.read_bytes()).hexdigest()
        check=next(r for r in audit['plates'] if r['plate']==row['plate'])
        assert digest==row['project_sha256']==check['project_sha256']
        assert hashlib.sha256((project.parent/'plate_1.gcode').read_bytes()).hexdigest()==check['gcode_sha256']
        with zipfile.ZipFile(project) as z:
            assert z.testzip() is None
            for name in z.namelist():
                if name.endswith(('.config','.model','.json','.xml')):
                    value=z.read(name).decode('utf8')
                    assert 'C:\\Users\\' not in value and 'C:/Users/' not in value
        files[project.name]=project.read_bytes()
    assert len(files)==2
    models=ROOT/'models/v4.2'
    for name in ('body-pin-clearance','lid-slide-lift','tray-middle-3','tray-top-3'):
        files['parts/'+name+'.stl']=(models/(name+'.stl')).read_bytes()
    for name in ('verification.json','tray-root-fix.json','tray-root-preview.png','support-removal.png','reinforcement-preview.png','floor-transition-preview.png'):
        files[name]=(models/name).read_bytes()
    files['README.zh-CN.md']=(ROOT/'docs/v4.2.zh-CN.md').read_text(encoding='utf8').replace('../models/v4.2/','').encode('utf8')
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    for path in sorted((ROOT/'docs/reports').glob('v4.2-*.json')):files['reports/'+path.name]=path.read_bytes()
    files['manifest.json']=json.dumps({'version':'4.2','release_tag':'v4.2','source_commit':commit,
        'scope':'complete four-part eight-DIMM case','complete_set_plates':2,
        'printer':'P2S / 0.4 mm','material':'PLA Basic','layer_height_mm':.2,
        'open_as_project':True,'supports_required':True,'side_holes_and_upper_arch_supports_blocked':True,
        'compatible_reusable_parts':['v4.1-rc4 lid'],
        'replace_body_and_upper_trays_for_all_fixes':True,'physical_complete_set_verified':False,'physical_impact_verified':False,
        'gcode_included':False},indent=2).encode()
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in files.items()).encode()
    out=ROOT/'build/rdimm-v4.2-complete-P2S.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h
    print(out)


if __name__=='__main__':main()
