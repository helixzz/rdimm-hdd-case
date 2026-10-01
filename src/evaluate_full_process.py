"""Whole-product process screening with fixed geometry and material strategy."""
import argparse,hashlib,json,subprocess,zipfile
from evaluate_full_product import OUT

VARIANTS={
    'axis-aligned':{'infill_direction':'0'},
    'wider-internal':{'internal_solid_infill_line_width':'0.5','sparse_infill_line_width':'0.5'},
    'combined-infill':{'infill_combination':'1'},
    'wide-combined':{'internal_solid_infill_line_width':'0.5','sparse_infill_line_width':'0.5','infill_combination':'1'},
}

def main(bambu):
    rows=[]
    for name,changes in VARIANTS.items():
        for plate in ('1-pin-clearance','2-upper-trays'):
            source=OUT/'dual-selective'/plate/'RESEARCH-not-released.3mf'
            with zipfile.ZipFile(source) as z:files={n:z.read(n) for n in z.namelist()}
            settings=json.loads(files['Metadata/project_settings.config']);new=dict(settings);new.update(changes)
            assert {k for k in new if new[k]!=settings.get(k)}==set(changes)
            files['Metadata/project_settings.config']=json.dumps(new).encode()
            folder=OUT/name/plate;folder.mkdir(parents=True,exist_ok=True);project=folder/'RESEARCH-not-released.3mf'
            with zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED) as z:
                for n,b in files.items():z.writestr(n,b)
            timed_out=False
            try:
                with (folder/'slice.log').open('wb') as log:
                    result=subprocess.run([str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)],cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                assert result.returncode==0,(name,plate,result.returncode)
            except subprocess.TimeoutExpired:
                assert (folder/'plate_1.gcode').read_text().rstrip().endswith('; EXECUTABLE_BLOCK_END');timed_out=True
            result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
            p=result['sliced_plates'][0]
            rows.append(dict(mode=name,plate=plate,seconds=p['total_predication'],filaments=p['filaments'],changes=p['filament_change_times'],warnings=p['warning_message'],features=p['feature_type_times'],
                process_changes=changes,geometry_and_paint_identical=True,cli_shutdown_timeout=timed_out,
                project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest()))
            (folder/'verification.json').write_bytes((OUT/'dual-selective'/plate/'verification.json').read_bytes())
            print(name,plate,p['total_predication'],flush=True)
        (OUT/(name+'-slicing.json')).write_text(json.dumps(rows[-2:],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',required=True);main(p.parse_args().bambu)
