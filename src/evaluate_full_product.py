"""Full-product DFM comparison. Research only; immutable releases are untouched."""
import argparse,hashlib,json,subprocess
import numpy as np
import evaluate_dfm_geometry as g
from build_v4_1 import CAPTURES
from check_bambu_v3 import read_mesh

ROOT=g.ROOT;OUT=ROOT/'build/full-product-study';v=g.v;base=g.base

def hole_voids():
    holes=v.m.Manifold();r=1.6
    for x in v.SIDE_X:
        for y,rot in ((-.1,(-90,0,0)),(v.W+.1,(90,0,0))):
            holes+=v.cyl(5.8,r,(x,y,6.35),rot=rot)+v.cyl(.41,r+.3,(x,y,6.35),r2=r,rot=rot)
    for x in v.BOTTOM_X:
        for y in v.BOTTOM_Y:holes+=v.cyl(5.4,r,(x,y,-.1))+v.cyl(.41,r+.3,(x,y,-.1),r2=r)
    return holes

def geometry(paddle):
    g.design.configure();p,f,l=base.parts()
    # Grow from the existing smaller-hole body, then cut the selected 3.2 mm
    # bore. Never leave a filled sleeve as a disconnected second solid.
    holes=hole_voids()
    p['body-pin-clearance']=(p['body-thread-pilot']-holes).set_tolerance(.001).simplify(.001)
    f['body-pin-clearance']=(f['body-thread-pilot']-holes).set_tolerance(.001).simplify(.001)
    for name in ('tray-middle-3','tray-top-3'):
        strip=v.box((4.661,.402,4.61),(1.89,94.899,-.1));cut=strip+strip.mirror((1,0,0)).translate((147,0,0))
        p[name]-=cut;f[name]-=cut
        p[name]=p[name].set_tolerance(.001).simplify(.001)
    if paddle:p,f,l=g.altered_parts(p,f,l,paddle=True)
    checks=base.verify(p,f,l,lid_up_probe=.55,mount_probe_radius=1.6)
    return p,f,l,checks

def make_parts(paddle=False,manual=False):
    p,f,l,checks=geometry(paddle);coupons=g.specimens('combined');a=coupons[0]
    placements=json.loads((ROOT/'models/v4.3/verification.json').read_text())['plate_records']
    plates=[];details=[]
    for label in ('1-pin-clearance','2-upper-trays'):
        record=next(r for r in placements if r['stem'].endswith(label));items=[]
        for pose in record['poses']:
            name=pose['part'];t=np.array(pose['assembly_to_plate']);cores=[];caps=[];motions=[];rois=[]
            if not name.startswith('lid'):
                count=2 if name.startswith('body') else 3;z=4. if count==2 else 0.
                for i,sy in enumerate(v.layout(count)[2]):
                    ty=l[name][i][0]-(2.8 if count==3 and i==0 else 0)
                    for j,core in enumerate(a['cores']):
                        shift=(0,sy-2.5 if j<2 else ty-14.5,z)
                        if manual:
                            cores.append(core.translate(shift));motions.append(1 if j<2 else -1)
                            caps.extend(c.translate(shift) for c in a['interfaces'][2*j:2*j+2])
                    if manual:
                        rois += [([6.29,sy+11.99,z+4.59],[7.92,sy+20.01,z+4.95]),
                                 ([139.38,ty+13.59,z+4.59],[142.01,ty+18.41,z+4.95])]
                if count==2 and manual:
                    for y,length in CAPTURES:
                        q=next(c for c in coupons if c.get('capture_length')==length)
                        for right in (False,True):
                            def move(s):
                                s=s.translate((0,y-2,19.2))
                                return s.mirror((1,0,0)).translate((147,0,0)) if right else s
                            cores += [move(c) for c in q['cores']];caps += [move(c) for c in q['interfaces']]
                            motions.append(-1 if right else 1)
                            rois.append(([140.599 if right else 2.39,y-.001,23.189],
                                         [144.61 if right else 6.401,y+length+.001,24.001]))
                for i,core in enumerate(cores):
                    for d in np.linspace(0,8,33):base.clear(core.translate((float(d)*motions[i],0,0)),p[name],(name,'core extraction',i,d))
                for i,s in enumerate(cores+caps):
                    base.clear(s,p[name],(name,'support overlaps product',i))
                    for q in (cores+caps)[:i]:base.clear(s,q,(name,'support overlap',i))
            def tx(s):return s.transform(t[:3,:])
            # Store local print coordinates (including lid inversion), leaving
            # translation zero so support selectors use exact plate coordinates.
            items.append(dict(name=name,kind=name,model=tx(p[name]),cores=[tx(s) for s in cores],interfaces=[tx(s) for s in caps],
                              translation=[0,0,0],inverse=np.linalg.inv(t).tolist(),rois=rois))
            details.append(dict(part=name,cores=len(cores),interfaces=len(caps),core_extraction_poses=len(cores)*33,assembly_to_plate=t.tolist()))
        plates.append((label,items))
    return plates,dict(checks=checks,mount_diameter_mm=3.2,details=details,outer_mm=[147,101.6,26],physical_verified=False)

def blocker(q,part,role):
    if role!='keep':return True
    t=np.array(part['inverse']);q=q@t[:3,:3].T+t[:3,3]
    if any(np.all(q>=lo)&np.all(q<=hi) for lo,hi in part['rois']):return True
    if not part['name'].startswith('body'):return False
    for y in (19.7,55.1):
        if np.all(q>=[145.399,y-.001,11.199]) and np.all(q<=[147.001,y+19.001,20.287]):return True
    for x in v.SIDE_X:
        for ya,yb in ((-.001,5.701),(v.W-5.701,v.W+.001)):
            if np.all(q>=[x-1.901,ya,4.449]) and np.all(q<=[x+1.901,yb,8.251]):return True
    for x in v.BOTTOM_X:
        for y in v.BOTTOM_Y:
            if np.allclose(q[:,2],5.3,atol=.001) and np.all(np.linalg.norm(q[:,:2]-[x,y],axis=1)<=1.601):return True
    return False

def export(items,folder,name,plate_xy_limits=(5.,245.)):
    lookup={p['kind']:p for p in items};old=(g.dual.parts,g.dual.VERSION,g.dual.should_block)
    try:
        g.dual.parts=lambda:items;g.dual.VERSION=name
        g.dual.should_block=lambda q,kind,role,length=0:blocker(q,lookup[kind],role)
        g.dual.build(folder,plate_xy_limits=plate_xy_limits)
    finally:g.dual.parts,g.dual.VERSION,g.dual.should_block=old
    manifest=json.loads((folder/'verification.json').read_text());manifest['scope']='Full product plate; manufacturing research, not released'
    (folder/'verification.json').write_text(json.dumps(manifest,indent=2))
    return folder/f'rdimm-{name}-plate-0-dual.3mf'

def run(bambu,modes):
    OUT.mkdir(parents=True,exist_ok=True);source=ROOT/'build/v4.4-rc3-dual-trial-projects/0-dual';rows=[]
    modespec={'single-control':(False,False,False),'single-paddle':(True,False,False),
              'dual-auto':(False,False,True),'dual-manual':(True,True,True),'dual-selective':(True,True,True)}
    for mode in modes:
        paddle,manual,dual=modespec[mode];plates,checks=make_parts(paddle,manual)
        (OUT/(mode+'-geometry.json')).write_text(json.dumps(checks,indent=2))
        for label,items in plates:
            folder=OUT/mode/label;folder.mkdir(parents=True,exist_ok=True)
            original=export(items,folder,'FULL-STUDY-'+mode+'-'+label)
            process=json.loads((source/'process.json').read_text())
            if dual:
                process['wipe_tower_x']=['12'];process['wipe_tower_y']=['150']
                if mode=='dual-selective':
                    process.update(support_interface_filament='1',support_top_z_distance='0.2',support_bottom_z_distance='0.2',
                                   support_interface_spacing='0.25',support_bottom_interface_spacing='0.25')
            else:
                process=json.loads((ROOT/f'build/v4.3-unpainted-projects/{label}/process.json').read_text())
                process['name']='Full product single-material control';process['print_settings_id']=process['name']
            (folder/'process.json').write_text(json.dumps(process))
            project=folder/'RESEARCH-not-released.3mf'
            filaments=str(source/'pla.json')+(';'+str(source/'support.json') if dual else '')
            commands=[[str(bambu),'--arrange','0','--load-settings',str(source/'machine.json')+';'+str(folder/'process.json'),
                       '--load-filaments',filaments,'--curr-bed-type','Textured PEI Plate','--export-3mf',str(project),str(original)],
                      [str(bambu),'--arrange','0','--slice','0','--outputdir',str(folder),str(project)]]
            shutdown_timeout=False
            for i,cmd in enumerate(commands):
                try:
                    with (folder/f'step-{i}.log').open('wb') as log:
                        r=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    assert r.returncode==0,(mode,label,i,r.returncode)
                except subprocess.TimeoutExpired as e:
                    assert i==1 and json.loads((folder/'result.json').read_text())['return_code']==0
                    assert (folder/'plate_1.gcode').read_text().rstrip().endswith('; EXECUTABLE_BLOCK_END')
                    shutdown_timeout=True
            a,b=read_mesh(original),read_mesh(project)
            assert np.array_equal(a.faces,b.faces) and np.allclose(a.vertices,b.vertices,atol=.000011,rtol=0)
            result=json.loads((folder/'result.json').read_text());assert result['return_code']==0
            p=result['sliced_plates'][0]
            row=dict(mode=mode,plate=label,seconds=p['total_predication'],changes=p['filament_change_times'],filaments=p['filaments'],warnings=p['warning_message'],features=p['feature_type_times'],cli_shutdown_timeout=shutdown_timeout,
                     gcode_sha256=hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),project_sha256=hashlib.sha256(project.read_bytes()).hexdigest())
            rows.append(row);print(json.dumps(row),flush=True)
        (OUT/(mode+'-slicing.json')).write_text(json.dumps(rows[-2:],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bambu');p.add_argument('--geometry-only',action='store_true')
    p.add_argument('--modes',nargs='+',default=['single-control','single-paddle','dual-auto','dual-manual','dual-selective'])
    a=p.parse_args()
    if a.geometry_only:
        OUT.mkdir(parents=True,exist_ok=True)
        for name,paddle,manual in [('single-control',False,False),('dual-selective',True,True)]:
            plates,checks=make_parts(paddle,manual)
            (OUT/(name+'-geometry.json')).write_text(json.dumps(checks,indent=2))
            print(name,checks['checks'],sum(x['core_extraction_poses'] for x in checks['details']),flush=True)
    else:
        if not a.bambu:p.error('--bambu is required for slicing')
        run(a.bambu,a.modes)
