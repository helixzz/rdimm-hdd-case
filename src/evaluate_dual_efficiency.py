"""Non-release slicing comparisons; preserve immutable RC3 inputs and purge volume."""
import argparse,copy,hashlib,json,subprocess,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
from build_dual_trial_v4_4_rc3 import ROOT,VERSION,NS

def main(bambu):
    source=ROOT/f'build/v{VERSION}-projects/0-dual'
    project=next(source.glob('*.3mf'))
    with zipfile.ZipFile(project) as z: original={n:z.read(n) for n in z.namelist()}
    baseline=json.loads((source/'result.json').read_text())['sliced_plates'][0]
    out=ROOT/'build/dual-efficiency';out.mkdir(exist_ok=True)
    rows=[]
    def record(name,copies,p):
        return dict(name=name,copies=copies,estimated_seconds=p['total_predication'],
                    changes=p['filament_change_times'],filaments=p['filaments'],
                    warnings=p['warning_message'],feature_seconds=p['feature_type_times'])
    rows.append(record('published-rc3',1,baseline))
    for name,copies,skip in [('skip-idle-tower',1,True),('two-copies',2,False),('two-copies-skip-idle-tower',2,True),('skip-idle-tower-far',1,True)]:
        folder=out/name;folder.mkdir(exist_ok=True)
        files=dict(original);settings=json.loads(files['Metadata/project_settings.config'])
        assert settings['flush_volumes_matrix']==['0','800','800','0']
        settings['wipe_tower_no_sparse_layers']=str(int(skip))
        if name.endswith('-far'):
            settings['wipe_tower_y']=['205']
        files['Metadata/project_settings.config']=json.dumps(settings).encode()
        if copies==2:
            # Same Z and orientation; second instance shifted92 mm along Y.
            # Coupon bounds45..190.1 /46.9..131 ->46.9..223, tower at205,165.
            root=E.fromstring(files['3D/3dmodel.model']);build=root.find('{'+NS+'}build')
            item=copy.deepcopy(build[0]);matrix=list(map(float,item.get('transform').split()));matrix[10]+=92
            item.set('transform',' '.join(map(str,matrix)))
            for key in list(item.attrib):
                if key.endswith('UUID'):item.set(key,'ebf97d92-c169-4b13-bd8a-d966bbcf30f9')
            build.append(item)
            E.register_namespace('',NS)
            E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
            files['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True)
        p=folder/'EXPERIMENT-not-released.3mf'
        with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
            for n,data in files.items():z.writestr(n,data)
        run=subprocess.run([str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(p)],cwd=folder,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (folder/'slice.log').write_bytes(run.stdout+run.stderr)
        result=json.loads((folder/'result.json').read_text())
        if run.returncode!=0 or result['return_code']!=0:
            row=dict(name=name,copies=copies,rejected=True,return_code=result['return_code'],reason=result['error_string'])
            rows.append(row);print(json.dumps(row));continue
        assert len(result['sliced_plates'])==1
        row=record(name,copies,result['sliced_plates'][0]);row['project_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        row['gcode_sha256']=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest()
        rows.append(row);print(json.dumps(row))
    report=dict(source_version=VERSION,source_project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
                changed_settings=['wipe_tower_no_sparse_layers','wipe_tower_y (far case only:165->205)'],two_copy_shift_mm=[0,92,0],
                purge_mm3_each_direction=800,physical_verified=False,release_files_changed=False,
                scope='Slicer estimates on coupons only; not full enclosure timing or print qualification',comparisons=rows)
    (out/'comparison.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',type=Path,required=True);main(p.parse_args().bambu)
