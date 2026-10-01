"""Two complete products on three specialized plates; no coupon extrapolation."""
import argparse,copy,hashlib,json,subprocess,zipfile
import numpy as np
import evaluate_full_product as f

def place(part,angle,xy,suffix):
    r=np.deg2rad(angle);t=np.eye(4);t[:2,:2]=[[np.cos(r),-np.sin(r)],[np.sin(r),np.cos(r)]]
    bounds=np.array(part['model'].transform(t[:3]).bounding_box()).reshape(2,3)
    t[:3,3]=[*xy,0]-bounds[0]
    q=dict(part);q['name']=part['name']+suffix;q['kind']=q['name']
    for key in ('cores','interfaces'):q[key]=[s.transform(t[:3]) for s in part[key]]
    q['model']=part['model'].transform(t[:3]);q['inverse']=(np.array(part['inverse'])@np.linalg.inv(t)).tolist()
    return q

def main(bambu):
    plates,checks=f.make_parts(True,True);body,lid=plates[0][1];middle,top=plates[1][1]
    bb=np.array(middle['model'].bounding_box()).reshape(2,3);a,b=bb[1,:2]-bb[0,:2];gap=4.;margin=(256-a-b-gap)/2
    layout=[(0,[margin,margin]),(90,[margin+a+gap,margin]),(180,[margin+b+gap,margin+a+gap]),(270,[margin,margin+b+gap])]
    batch=[('2-bodies',[place(body,0,[54.5,20],'a'),place(body,0,[54.5,130],'b')],True),
           ('2-lids',[place(lid,0,[56.3,20],'a'),place(lid,0,[56.3,130],'b')],False),
           ('4-trays',[place(q,angle,xy,str(i)) for i,(q,(angle,xy)) in enumerate(zip([middle,top,middle,top],layout))],True)]
    rows=[]
    for label,parts,dual in batch:
        folder=f.OUT/'batch-two'/label;folder.mkdir(parents=True,exist_ok=True)
        for i,q in enumerate(parts):
            for p in parts[:i]:f.base.clear(q['model'],p['model'],'batch model collision')
        original=f.export(parts,folder,'BATCH-STUDY-'+label,plate_xy_limits=(5,251))
        process=json.loads((f.OUT/'dual-selective'/'1-pin-clearance'/'process.json').read_text())
        if not dual:process=json.loads((f.ROOT/'build/v4.3-unpainted-projects/1-pin-clearance/process.json').read_text())
        if label=='4-trays':process['wipe_tower_x']=['110.5'];process['wipe_tower_y']=['110.5']
        (folder/'process.json').write_text(json.dumps(process));source=f.ROOT/'build/v4.4-rc3-dual-trial-projects/0-dual'
        filament=str(source/'pla.json')+(';'+str(source/'support.json') if dual else '')
        project=folder/'RESEARCH-not-released.3mf'
        cmds=[[bambu,'--arrange','0','--load-settings',str(source/'machine.json')+';'+str(folder/'process.json'),
               '--load-filaments',filament,'--curr-bed-type','Textured PEI Plate','--export-3mf',str(project),str(original)],
              [bambu,'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
        for i,cmd in enumerate(cmds):
            with (folder/f'step-{i}.log').open('wb') as log:
                r=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            assert r.returncode==0,(label,i,r.returncode)
        a0,b0=f.read_mesh(original),f.read_mesh(project)
        assert np.array_equal(a0.faces,b0.faces) and np.allclose(a0.vertices,b0.vertices,atol=.000011,rtol=0)
        result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
        p=result['sliced_plates'][0]
        row=dict(plate=label,seconds=p['total_predication'],changes=p['filament_change_times'],filaments=p['filaments'],warnings=p['warning_message'],features=p['feature_type_times'],
                 project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest())
        rows.append(row);print(json.dumps(row),flush=True)
    report=dict(products=2,plates=3,results=rows,tray_body_margin_mm=float(margin),tray_model_gap_mm=gap,
                checks=checks,scope='Two complete products; unprinted research layout, not a release or proven global packing optimum.')
    (f.OUT/'batch-two-slicing.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu',required=True);main(p.parse_args().bambu)
