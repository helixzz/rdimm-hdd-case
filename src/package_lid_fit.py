"""Package a versioned single replacement lid after source/report commit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main(version='4.1-rc3'):
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    folder=ROOT/f'build/v{version}-projects'
    audit=json.loads((folder/'finite-width-audit.json').read_text(encoding='utf8'))['plates'][0]
    project=next((folder/'3-replacement-lid').glob('*P2S*.3mf'))
    assert hashlib.sha256(project.read_bytes()).hexdigest()==audit['project_sha256']
    assert hashlib.sha256((project.parent/'plate_1.gcode').read_bytes()).hexdigest()==audit['gcode_sha256']
    with zipfile.ZipFile(project) as z:assert z.testzip() is None
    files={project.name:project.read_bytes()}
    files['README.zh-CN.md']=(ROOT/f'docs/v{version}.zh-CN.md').read_text(encoding='utf8').replace(f'../models/v{version}/','').encode('utf8')
    for name in ('lid-fit-preview.png','lid-fit.json','verification.json'):
        files[name]=(ROOT/f'models/v{version}'/name).read_bytes()
    for p in (ROOT/'docs/reports').glob(f'v{version}-*.json'):files['reports/'+p.name]=p.read_bytes()
    files['manifest.json']=json.dumps({'version':version,'scope':'replacement lid only','plates':1,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'compatible_body_trays':['4.1-rc1','4.1-rc2'],'open_as_project':True,'supports_required':True,
        'printer':'P2S / 0.4 mm','material':'PLA Basic','layer_height_mm':.2,'physical_fit_verified':False,
        'physical_strength_verified':False,'gcode_included':False},indent=2).encode('utf8')
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in files.items()).encode()
    out=ROOT/f'build/rdimm-v{version}-replacement-lid-P2S.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,b in files.items():z.writestr(name,b)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print(out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',choices=['4.1-rc3','4.1-rc4'],default='4.1-rc3')
    main(parser.parse_args().version)
