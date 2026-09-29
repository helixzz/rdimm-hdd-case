"""V4 RC1: integrated bottom, lift-off sliding lid, corrected connector side.

Rigid geometry/path checks are not print, support-removal or force validation.
"""
from pathlib import Path
from itertools import product
import argparse
import json
import zipfile
import numpy as np
import trimesh
import manifold3d as m
import build_v3_2 as rc
from operation_marks import lettering, top_cut, down_arrow, DEPTH

ROOT=Path(__file__).resolve().parents[1]
v3=rc.v3
VERSION='4.0-rc1'
SATA_DEPTH=6.
SIDE_MARKS=True
FLOOR_FILLET_RADIUS=0.
SHELL_LEAF=rc.leaf
PART_MODIFIER=None
SATA_Y=v3.W-58.  # TOP view, X=0 connector end: mirror the mistaken bottom-view datum.


def parts():
    p={}; fixed={}; leaves={}
    _,bottom_fixed,bottom_leaves=rc.revised_tray('tray-bottom-2',2,False,'1')
    # No separate floor/labelled lift rail for the now permanently fixed bottom.
    for sy in v3.layout(2)[2]:
        bottom_fixed-=v3.box((130.2,31.8,.8),(8.4,sy,0))
    old_mark=top_cut(lettering('1 LIFT').rotate(90).translate((5.6,44.)),6.8)
    bottom_fixed+=old_mark^v3.box((4.4,65.4,.3),(1.9,18.1,6.5))
    bottom_fixed-=top_cut(lettering('1 BASE').rotate(90).translate((5.6,44.)),6.8)
    bottom_fixed=bottom_fixed.translate((0,0,4.))
    for x,y in v3.KEYS:bottom_fixed+=v3.cyl(1.3,1.31,(x,y,4.))
    bottom_leaves=[(y,s.translate((0,0,4.))) for y,s in bottom_leaves]
    for name in ('body-pin-clearance','body-thread-pilot'):
        pin=name.endswith('clearance')
        # Retain the original source defaults so old releases rebuild unchanged.
        a=v3.body(pin,sata_y=SATA_Y,full_rails=False,sata_depth=SATA_DEPTH)
        if SIDE_MARKS:
            front=lettering('PRESS').translate((66.3,12.5))+down_arrow(73.5,16.8,18.7,1.,1.5)
            a-=front.extrude(DEPTH+.1).rotate((90,0,0)).translate((0,DEPTH,0))
            a-=lettering('SATA END').extrude(DEPTH+.1).transform([[0,0,-1,DEPTH],[-1,0,0,44.],[0,1,0,9.2]])
        a-=v3.box((31,1.8,7),(47,0,20))
        for y in (7.,88.6):
            piece=v3.rail(6.).translate((0,y,0))+v3.box((1.6,6.,.02),(0,y,24.39))
            a+=piece+piece.mirror((1,0,0)).translate((147,0,0))
        a+=bottom_fixed
        # The bottom flexures must NOT fuse along their feet to the body floor.
        for y,_ in bottom_leaves:
            a-=v3.box((5.9,19.,2.),(141.1,y,2.2))
            # Open the whole beam length to the outside for support removal and
            # finger release; no blind support tunnel and no HDD holes here.
            a-=v3.box((5.9,19.,24.),(141.1,y,2.2))
        # Cut after merging so the old tray cannot refill the new socket cavity.
        a-=v3.box((SATA_DEPTH+.1,47.,6.3),(-.1,SATA_Y,-.1))
        if FLOOR_FILLET_RADIUS:
            from floor_fillet import fillets,mount_voids
            a+=fillets(FLOOR_FILLET_RADIUS)-mount_voids(pin)
        fixed[name]=a.set_tolerance(.0001)
        leaves[name]=bottom_leaves
        a+=SHELL_LEAF()
        for _,s in bottom_leaves:a+=s
        p[name]=a.set_tolerance(.0001)
    lid=rc.old_part('lid-slide')
    for y in (14.6,96.2):
        for x in (0.,143.4):lid-=v3.box((3.6,6.8,3.),(x,y,24.))
    lid-=top_cut(lettering('3 LIFT').translate((64.75,44.)),26.)
    p['lid-slide-lift']=lid
    for name,tier in [('tray-middle-3','2'),('tray-top-3','3')]:
        p[name],fixed[name],leaves[name]=rc.revised_tray(name,3,False,tier)
    return PART_MODIFIER(p,fixed,leaves) if PART_MODIFIER else (p,fixed,leaves)


def clear(a,b,label):
    volume=(a^b).volume()
    assert volume<.001,(label,volume)


def verify(p,fixed,leaves,lid_up_probe=.4):
    checks={'module_poses':0,'loaded_tray_entry_poses':0,'bottom_release_poses':0,'lid_poses':0}
    body=p['body-pin-clearance'];lid=p['lid-slide-lift']
    assembly=[body,lid,p['tray-middle-3'].translate((0,0,10.8)),p['tray-top-3'].translate((0,0,17.6))]
    for i,a in enumerate(assembly):
        for b in assembly[:i]:clear(a,b,('assembly',i))
    for a in assembly[1:]:clear(a,p['body-thread-pilot'],'pilot assembly')
    for n,seat in [(2,4.),(3,10.8),(3,17.6)]:
        for sy in v3.layout(n)[2]:
            for length,width,pcb in product((133.2,133.8),(31.1,31.4),(1.17,1.37)):
                for x,y,z in product((6.5,140.5-length),(sy+.1,sy+31.7-width),(3.,4.6-pcb)):
                    ram=rc.simple.module(length,width,pcb,x,y,z).translate((0,0,seat))
                    for a in assembly:clear(ram,a,('module',n,seat,x,y,z))
                    checks['module_poses']+=1
    # Loaded trays must pass through the open mouth without deforming the body.
    for name,seat in [('tray-middle-3',10.8),('tray-top-3',17.6)]:
        loaded=p[name]
        for sy in v3.layout(3)[2]:loaded+=rc.simple.module(133.8,31.4,1.37,6.6,sy+.2)
        for z in np.linspace(30.,seat,121):
            clear(loaded.translate((0,0,float(z))),body,('tray entry',name,z))
            checks['loaded_tray_entry_poses']+=1
    # Body leaf deflection is illustrative, based on the physically returning A.
    static=fixed['body-pin-clearance']
    for _,s in leaves['body-pin-clearance']:static+=s
    for t in np.linspace(0,2.5,26):
        moved=SHELL_LEAF().warp(lambda q:(q[0],q[1],q[2]-float(t)*max(0,min(1,(q[0]-47)/30))**2))
        clear(moved,static,'shell leaf sweep')
    released=static+moved
    for dy in np.linspace(0,8,81):
        for a in [released]+assembly[2:]:clear(lid.translate((0,-float(dy),0)),a,('slide',dy))
        checks['lid_poses']+=1
    for dz in np.linspace(0,10,51):
        for a in [released]+assembly[2:]:clear(lid.translate((0,-8,float(dz))),a,('lift',dz))
        checks['lid_poses']+=1
    for direction in [(0,-1,0),(0,1,0),(0,0,lid_up_probe),(0,0,-.3)]:
        assert (lid.translate(direction)^body).volume()>.01,('missing lid stop',direction)
    for rotation in [(2,0,0),(-2,0,0),(0,2,0),(0,-2,0)]:
        tipped=lid.translate((-73.5,-50.8,-24.4)).rotate(rotation).translate((73.5,50.8,24.4))
        assert (tipped^body).volume()>.01,('lid tipping stop',rotation)
    assert (assembly[-1].translate((0,0,.4))^lid).volume()>.01
    assert (assembly[2].translate((0,0,.3))^assembly[3]).volume()>.01
    # Integrated bottom releases must work while still inside the shell.
    for i,(y,s) in enumerate(leaves['body-pin-clearance']):
        other=fixed['body-pin-clearance']+SHELL_LEAF()
        for j,(_,q) in enumerate(leaves['body-pin-clearance']):
            if i!=j:other+=q
        for t in np.linspace(0,1.5,31):clear(rc.simple.bend(s,y,float(t)),other,('bottom beam',i,t))
        opened=other+rc.simple.bend(s,y)
        sy=v3.layout(2)[2][i]
        for length,width,pcb in product((133.2,133.8),(31.1,31.4),(1.17,1.37)):
            ram=rc.simple.module(length,width,pcb,6.55,sy+.2)
            poses=[rc.tilt(ram,6.55,float(a)) for a in np.linspace(0,2,21)]
            poses += [rc.tilt(ram,6.55,2.).translate((float(dx),0,0)) for dx in np.linspace(0,2,21)]
            poses += [rc.tilt(ram,6.55,2.).translate((2.,0,float(dz))) for dz in np.linspace(0,26,53)]
            for q in poses:
                clear(q.translate((0,0,4.)),opened,('bottom DIMM removal',i,length,width,pcb))
                checks['bottom_release_poses']+=1
    probes=[v3.box((SATA_DEPTH,47.,6.2),(0,SATA_Y,0))]
    for x in v3.SIDE_X:
        probes += [v3.cyl(5.,1.8,(x,0,6.35),rot=(-90,0,0)),v3.cyl(5.,1.8,(x,v3.W,6.35),rot=(90,0,0))]
    for x in v3.BOTTOM_X:
        for y in v3.BOTTOM_Y:probes.append(v3.cyl(5.,1.8,(x,y,0)))
    for probe in probes:
        for a in assembly:clear(a,probe,'mount/socket probe')
    # Upper cartridges retain their RC1 clip release and PCB stops. Test again
    # because these parts, while unchanged, are included in this distribution.
    for name in ('tray-middle-3','tray-top-3'):
        for i,(y,s) in enumerate(leaves[name]):
            other=fixed[name]
            for j,(_,q) in enumerate(leaves[name]):
                if i!=j:other+=q
            for t in np.linspace(0,1.5,16):clear(rc.simple.bend(s,y,float(t)),other,'upper leaf')
            opened=other+rc.simple.bend(s,y)
            sy=v3.layout(3)[2][i]
            ram=rc.simple.module(133.8,31.4,1.37,6.55,sy+.2)
            for angle in np.linspace(0,2,21):clear(rc.tilt(ram,6.55,float(angle)),opened,'upper tilt')
            for dx in np.linspace(0,2,21):clear(rc.tilt(ram,6.55,2.).translate((float(dx),0,0)),opened,'upper withdrawal')
        for sy in v3.layout(3)[2]:
            for pos in ((6.45,sy+.2,3.),(6.75,sy+.2,3.),(6.6,sy+.05,3.),(6.6,sy+.35,3.),(6.6,sy+.2,2.95),(6.6,sy+.2,3.28)):
                assert (v3.box((133.8,31.4,1.37),pos)^p[name]).volume()>.0001
    for sy in v3.layout(2)[2]:
        for pos in ((6.45,sy+.2,7.),(6.75,sy+.2,7.),(6.6,sy+.05,7.),(6.6,sy+.35,7.),(6.6,sy+.2,6.95),(6.6,sy+.2,7.28)):
            assert (v3.box((133.8,31.4,1.37),pos)^body).volume()>.0001,('bottom PCB stop',pos)
    for name,s in p.items():
        assert len(s.decompose())==1,(name,'disconnected')
        mesh=v3.meshof(s);assert mesh.is_watertight and mesh.is_winding_consistent,name
    bounds=np.array([v3.meshof(a).bounds for a in assembly])
    assert np.allclose(bounds[:,0].min(0),[0,0,0],atol=.0001)
    assert np.allclose(bounds[:,1].max(0),[147,101.6,26],atol=.0001)
    return checks


def build(out,lid_up_probe=.4):
    out.mkdir(parents=True,exist_ok=True)
    p,fixed,leaves=parts()
    checks=verify(p,fixed,leaves,lid_up_probe=lid_up_probe)
    meshes={};transforms={}
    for name,s in p.items():
        mesh=v3.meshof(s);t=np.eye(4)
        if name.startswith('lid'):
            t=trimesh.transformations.rotation_matrix(np.pi,[1,0,0]);mesh.apply_transform(t)
        shift=-mesh.bounds[0];mesh.apply_translation(shift);t[:3,3]+=shift
        mesh.export(out/(name+'.stl'));meshes[name]=mesh;transforms[name]=t
    layouts={
        'plate-1-pin-clearance':[('body-pin-clearance',54.5,20.),('lid-slide-lift',56.3,130.)],
        'plate-1-thread-pilot':[('body-thread-pilot',54.5,20.),('lid-slide-lift',56.3,130.)],
        'plate-2-upper-trays':[('tray-middle-3',56.4,20.),('tray-top-3',56.4,128.)],
    }
    records=[]
    for label,items in layouts.items():
        packed=[];poses=[]
        for name,x,y in items:
            mesh=meshes[name].copy();shift=np.array([x,y,0.])-mesh.bounds[0]
            mesh.apply_translation(shift);t=transforms[name].copy();t[:3,3]+=shift
            assert mesh.bounds[0,:2].min()>=10 and mesh.bounds[1,:2].max()<=246
            for b in packed:
                gap=np.maximum(0,np.maximum(mesh.bounds[0,:2]-b.bounds[1,:2],b.bounds[0,:2]-mesh.bounds[1,:2]))
                assert np.linalg.norm(gap)>=8
            packed.append(mesh);poses.append({'part':name,'assembly_to_plate':t.tolist()})
        mesh=trimesh.util.concatenate(packed);stem='rdimm-'+VERSION+'-'+label
        mesh.export(out/(stem+'.stl'));rc.export_geometry(out/(stem+'.3mf'),mesh)
        path=out/(stem+'.3mf')
        with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
        data['3D/3dmodel.model']=data['3D/3dmodel.model'].replace(b'case v3.1',('case v'+VERSION).encode())
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for n,value in data.items():z.writestr(n,value)
        records.append({'stem':stem,'poses':poses,'bounds':mesh.bounds.tolist()})
    report={'version':VERSION,'status':'candidate, unprinted','capacity':8,'part_count':4,'complete_set_plates':2,
            'plate_count_global_minimum_proven':False,'outer_mm':[147,101.6,26],
            'sata_cavity_mm':{'min':[0,SATA_Y,0],'max':[SATA_DEPTH,SATA_Y+47,6.2]},
            'lid_opening':'Press, slide 8 mm toward -Y, lift; reverse to close',
            'checks':checks,'plate_records':records,'supports_required':True,
            'physical_tested':False,'force_fatigue_verified':False,'geometry_only_3mf':True}
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'build/v4.0-rc1')
    build(parser.parse_args().output_dir.resolve())
