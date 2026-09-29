"""Package the verified local V4.1 projects, instructions and checksums."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Commit source and reports before delivery'
    source=ROOT/'build/v4.1-rc1-p1-projects'
    report=json.loads((source/'slicing-report.json').read_text(encoding='utf8'))
    audit=json.loads((source/'finite-width-audit.json').read_text(encoding='utf8'))
    files={}
    for row in report['results']:
        path=source/row['plate']/row['project'];data=path.read_bytes()
        digest=hashlib.sha256(data).hexdigest()
        assert digest==row['project_sha256']
        check=next(a for a in audit['plates'] if a['plate']==row['plate'])
        assert digest==check['project_sha256']
        assert hashlib.sha256((path.parent/'plate_1.gcode').read_bytes()).hexdigest()==check['gcode_sha256']
        with zipfile.ZipFile(path) as z:assert z.testzip() is None
        files[path.name]=data
    text=(ROOT/'docs/v4.1-rc1.zh-CN.md').read_text(encoding='utf8')
    files['README.zh-CN.md']=text.replace('../models/v4.1-rc1/','').encode('utf8')
    for name in ('reinforcement-preview.png','support-removal.png','reinforcement.json','verification.json'):
        files[name]=(ROOT/'models/v4.1-rc1'/name).read_bytes()
    for path in sorted((ROOT/'docs/reports').glob('v4.1-rc1-*.json')):
        files['reports/'+path.name]=path.read_bytes()
    files['manifest.json']=json.dumps({'version':'4.1-rc1','process':'p1',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'matched_complete_set_required':True,'printer':'P2S / 0.4 mm','material':'PLA Basic',
        'layer_height_mm':.2,'bambu_version':'02.08.02.61','open_as_project':True,
        'complete_set_plates':2,'physical_impact_verified':False,'physical_cycles_verified':False,
        'gcode_included':False},indent=2).encode()
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in files.items()).encode()
    out=ROOT/'build/rdimm-v4.1-rc1-P2S-print-projects.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1)
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print(out)


if __name__=='__main__':main()
