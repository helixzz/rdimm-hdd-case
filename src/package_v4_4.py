"""Package exactly two configured full-product projects from a clean v4.4 tag."""
import hashlib,json,subprocess,zipfile
from build_v4_4 import ROOT,VERSION

def main():
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert commit==subprocess.check_output(['git','rev-parse','v4.4^{commit}'],cwd=ROOT,text=True).strip()
    folder=ROOT/'build/v4.4-projects';models=ROOT/'models/v4.4'
    report=json.loads((folder/'slicing-report.json').read_text());audit=json.loads((folder/'toolpath-audit.json').read_text())
    assert len(report['results'])==2 and sum(len(a['inserts']) for a in audit['plates'])==20
    files={'LICENSE':(ROOT/'LICENSE').read_bytes()}
    for r,a in zip(report['results'],audit['plates']):
        assert r['plate']==a['plate'];path=folder/r['plate']/r['project']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==r['project_sha256']==a['project_sha256']
        assert hashlib.sha256((path.parent/'plate_1.gcode').read_bytes()).hexdigest()==r['gcode_sha256']==a['gcode_sha256']
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None and not any(n.endswith('.gcode') for n in z.namelist())
            for n in z.namelist():
                if n.endswith(('.config','.model','.json','.xml')):
                    s=z.read(n).decode('utf8');assert 'C:/Users/' not in s and 'C:\\Users\\' not in s
        files[path.name]=path.read_bytes()
    for name in ('verification.json','tray-root-fix.json','plate-guide.png','support-removal.png'):
        files[name]=(models/name).read_bytes()
    for p in sorted(models.glob('*.stl')):files['geometry-reference-only/'+p.name]=p.read_bytes()
    assert sum(n.endswith('.stl') for n in files)==4
    for public,local in [('slicing','slicing-report'),('toolpath','toolpath-audit'),('roots','root-bead-audit'),('teeth','tooth-clearance-audit'),('ordinary-support','ordinary-support-audit')]:
        p=ROOT/f'docs/reports/v4.4-{public}.json';assert p.read_bytes()==(folder/(local+'.json')).read_bytes();files['reports/'+p.name]=p.read_bytes()
    files['README.zh-CN.md']=(ROOT/'docs/v4.4.zh-CN.md').read_text(encoding='utf8').replace('../models/v4.4/','').encode('utf8')
    files['manifest.json']=json.dumps(dict(version=VERSION,release_tag='v4.4',source_commit=commit,
        scope='complete four-part eight-DIMM product',complete_set_plates=2,
        printer='P2S / 0.4 mm',ams='AMS 2 Pro',layer_height_mm=.2,
        logical_materials={'1':'Bambu PLA Basic / GFA00','2':'Bambu Support For PLA / GFS02'},map_to_actual_AMS_slots=True,
        open_as_project=True,print_sequence='by layer',dedicated_supports=20,automatic_supports_required=True,
        selected_mount_diameter_mm=3.2,prime_tower_required=True,
        coupon_evidence='RC6: clean support removal, tools required at fixed/C',physical_complete_set_verified=False,
        physical_impact_verified=False,gcode_included=False),indent=2).encode()
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in files.items()).encode()
    target=ROOT/'build/rdimm-v4.4-complete-P2S-AMS2Pro.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None and sum(n.endswith('.3mf') for n in z.namelist())==2
        assert not any(n.endswith('.gcode') for n in z.namelist())
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h
    target.with_suffix('.zip.sha256').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    print(target)

if __name__=='__main__':main()
