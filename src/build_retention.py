"""V2-R retrofit: keep the v2 body; replace trays and lid and add PCB keepers.
No physical transport or fastener-strength certification is implied.
"""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import json
import manifold3d as m
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--models', type=Path, default=ROOT / 'models/v2')
parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/v2-retention')
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
original = json.loads((args.models/'verification.json').read_text())
records = {r['part']: r for r in original['parts']}
L, W, H = 147., 101.6, 26.
BASE, PITCH, BODY_H, LID_T = 4., 6.8, 24.4, 1.6
SLOT_X, SLOT_L, SLOT_W = 6.3, 134.4, 31.8
SHELF_Z, ROOF_Z = 3., 4.5
RAIL_TOP = 5.6
TIES = [(4.1, 40.), (142.9, 61.6)]
LID_POSTS = [(x,y) for x in (3.,144.) for y in (10.,91.6)]


def box(size, pos=(0,0,0)):
    return m.Manifold.cube(size).translate(pos)


def cylinder(height, radius, pos, top_radius=-1):
    return m.Manifold.cylinder(height, radius, top_radius, circular_segments=64).translate(pos)


def meshof(s):
    q = s.to_mesh()
    mesh = trimesh.Trimesh(np.asarray(q.vert_properties)[:,:3], np.asarray(q.tri_verts), process=True)
    mesh.merge_vertices(digits_vertex=4)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    return mesh


def original_solid(name):
    mesh = trimesh.load_mesh(args.models/(name+'.stl'))
    mesh.apply_translation(-np.asarray(records[name]['translation_for_print']))
    if name == 'lid':
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
    mesh.vertices = np.round(mesh.vertices,4)
    mesh.merge_vertices()
    return m.Manifold(m.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))


def opposite(s):
    return s.rotate((0,0,180)).translate((L,W,0))


def layout(n):
    width = n*SLOT_W+(n-1)*.6+1.2
    y = (W-width)/2
    return width,y,[y+.6+i*(SLOT_W+.6) for i in range(n)]


def fastening_y(n):
    ys = [y+SLOT_W/2 for y in layout(n)[2]]
    return [ys[0],ys[-1]] if n>1 else [ys[0]-8,ys[0]+8]


def keeper(n):
    width,y,_ = layout(n)
    a = box((6.,width,1.2),(1.9,y,RAIL_TOP))
    a += box((1.1,width,RAIL_TOP-ROOF_Z),(6.8,y,ROOF_Z))
    for x,py in LID_POSTS:
        a -= box((6.5,6.6,8),(x-3.25,py-3.3,0))
    for py in fastening_y(n):
        a -= cylinder(8,1.1,(4.1,py,0))
        a -= cylinder(1.05,1.1,(4.1,py,PITCH-1.05),2.15)
    if n>1:
        a -= cylinder(8,1.2,(4.1,40.,0))
    return a


def tray(name,n,bottom=False):
    a = original_solid(name)
    width,y,ys = layout(n)
    rail = box((4.4,width,RAIL_TOP),(1.9,y,0))
    a += rail + opposite(rail)
    # Seat keeper tops at the existing 6.8 mm layer pitch. Relieve dividers
    # below the PCB-only lip, never leave a keeper perched on a divider.
    cut = box((6.3,width+.2,2),(1.8,y-.1,RAIL_TOP))
    cut += box((1.5,width+.2,1.3),(6.6,y-.1,4.4))
    a -= cut + opposite(cut)
    for sy in ys:
        # Fused guide extensions: PCB stops 0.1 mm before the broad cavity wall.
        for gy in (sy,sy+SLOT_W-.1):
            g = box((1.6,.1,1.5),(SLOT_X,gy,SHELF_Z-.1))
            a += g + opposite(g)
        # Length stop acts only on the blank PCB end, below the keeper roof.
        g = box((.2,SLOT_W,1.5),(SLOT_X,sy,SHELF_Z-.1))
        a += g + opposite(g)
    for x,py in LID_POSTS:
        a -= box((6.5,6.6,8),(x-3.25,py-3.3,-.1))
    for py in fastening_y(n):
        hole = cylinder(4.7,.8,(4.1,py,1.0))
        a -= hole + opposite(hole)
    if n>1:
        for x,py in TIES:
            a -= cylinder(4.7,.8,(x,py,1.0)) if bottom else cylinder(8,1.2,(x,py,-.1))
    return a


def lid():
    a = original_solid('lid')
    for x,y in TIES:
        # Pads bridge the old 0.2 mm recess to bear directly on keeper rails.
        a += box((4.4,7,.3),(x-2.2,y-3.5,0))
        a -= cylinder(2,1.1,(x,y,-.1))
        a -= cylinder(1.05,1.1,(x,y,LID_T-1.05),2.15)
    return a


parts = {
    'tray-bottom-2':tray('tray-bottom-2',2,True),
    'tray-middle-3':tray('tray-middle-3',3),
    'tray-top-3':tray('tray-top-3',3),
    'keeper-2-print-2':keeper(2),
    'keeper-3-print-4':keeper(3),
    'lid-retention':lid(),
    'test-tray-1':tray('fit-coupon-1-slot-print-3',1),
    'test-keeper-1-print-2':keeper(1),
}
# STL coordinates are float32. Remove sub-micron Boolean slivers at shared
# source/added faces before re-export; this is far below printing tolerances.
parts = {name:s.set_tolerance(.0001) for name,s in parts.items()}
checks = []
for name,s in parts.items():
    mesh = meshof(s)
    assert len(s.decompose())==1, (name,'disconnected')
    if name.startswith('keeper') or name.startswith('test-keeper') or name.startswith('lid'):
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
    mesh.apply_translation(-mesh.bounds[0])
    mesh.export(OUT/(name+'.stl'))
    read = trimesh.load_mesh(OUT/(name+'.stl'))
    assert read.is_watertight and read.is_winding_consistent, name
    assert abs(read.volume-s.volume()) < .02, (name,'mesh cleanup changed volume')
    checks.append({'part':name,'extents_mm':read.extents.tolist(),'volume_cm3':s.volume()/1000,'single_closed_solid':True})

body = original_solid('body-pilot')
assembled = [body,parts['lid-retention'].translate((0,0,BODY_H))]
for tier,(n,name) in enumerate(((2,'tray-bottom-2'),(3,'tray-middle-3'),(3,'tray-top-3'))):
    z = BASE+tier*PITCH
    cap = parts['keeper-2-print-2' if n==2 else 'keeper-3-print-4']
    assembled.extend([parts[name].translate((0,0,z)),cap.translate((0,0,z)),opposite(cap).translate((0,0,z))])
for i,a in enumerate(assembled):
    for j,b in enumerate(assembled[:i]):
        assert (a^b).volume()<1e-5, ('assembly overlap',i,j,(a^b).volume())
for a in assembled[1:]:
    assert (a^original_solid('body-side-inserts')).volume()<1e-5

# Load paths: M2x5 keeper screws and M2x20 tie screws, avoiding RAM/other screws.
# Threads intentionally engage plastic; only unexpected metal/metal and RAM
# intersections are checked. This does not predict plastic thread strength.
screws=[]
for tier,n in enumerate((2,3,3)):
    z=BASE+tier*PITCH
    for py in fastening_y(n):
        a=cylinder(5,1.,(4.1,py,z+PITCH-5))
        a+=cylinder(1.05,1.1,(4.1,py,z+PITCH-1.05),2.15)
        screws.extend([a,opposite(a)])
for x,y in TIES:
    a=cylinder(20,1.,(x,y,H-20))
    a+=cylinder(1.05,1.1,(x,y,H-1.05),2.15)
    screws.append(a)
for i,a in enumerate(screws):
    for b in screws[:i]:assert (a^b).volume()<1e-5

# Actual mechanical-travel endpoints: PCB bears on shelf/roof/end guides.
# Module dimensions vary across the reference drawing's tolerances. Components
# retain the unverified 2 mm short-edge keep-out assumption.
cases=0
for tier,n in enumerate((2,3,3)):
    z=BASE+tier*PITCH
    for sy in layout(n)[2]:
        for length,width,pcb in product((133.2,133.8),(31.1,31.4),(1.17,1.37)):
            for bx,by,bz in product((6.5,140.5-length),(sy+.1,sy+SLOT_W-.1-width),(z+SHELF_Z,z+ROOF_Z-pcb)):
                board=box((length,width,pcb),(bx,by,bz))
                chips=box((length-4,width,pcb+4.2),(bx+2,by,bz-2.1))
                module=board+chips
                for a in assembled+screws:
                    assert (a^module).volume()<1e-5, ('module overlap',tier,sy,length,width,pcb,bx,by,bz,(a^module).volume())
                cases+=1

# Negative controls: a PCB moved 0.05 mm beyond each permitted direction must
# encounter a physical stop. A missing roof/guide must fail, not merely become
# a more spacious collision-free model.
stop_checks=0
for tier,n in enumerate((2,3,3)):
    z=BASE+tier*PITCH
    for sy in layout(n)[2]:
        poses=[(6.45,sy+.2,z+3.),(6.75,sy+.2,z+3.),
               (6.6,sy+.05,z+3.),(6.6,sy+.35,z+3.),
               (6.6,sy+.2,z+2.95),(6.6,sy+.2,z+ROOF_Z-1.37+.05)]
        for pos in poses:
            pcb=box((133.8,31.4,1.37),pos)
            assert sum((pcb^a).volume() for a in assembled)>.0001, ('missing PCB stop',tier,sy,pos)
            stop_checks+=1

# Empty/full single-slot test assembly; keepers use four M2x5 screws total.
coupon=[parts['test-tray-1'],parts['test-keeper-1-print-2'],opposite(parts['test-keeper-1-print-2'])]
for i,a in enumerate(coupon):
    for b in coupon[:i]:assert (a^b).volume()<1e-5
coupon_cases=0
sy=layout(1)[2][0]
for length,width,pcb in product((133.2,133.8),(31.1,31.4),(1.17,1.37)):
    for bx,by,bz in product((6.5,140.5-length),(sy+.1,sy+SLOT_W-.1-width),(SHELF_Z,ROOF_Z-pcb)):
        module=box((length,width,pcb),(bx,by,bz))+box((length-4,width,pcb+4.2),(bx+2,by,bz-2.1))
        for a in coupon:assert (a^module).volume()<1e-5
        coupon_cases+=1
bounds=np.array([meshof(p).bounds for p in assembled])
assert np.allclose(bounds[:,0,:].min(0),[0,0,0],atol=1e-5)
assert np.allclose(bounds[:,1,:].max(0),[L,W,H],atol=1e-5)

report={
 'variant':'v2-retention','reuse':'v2 body only; replace all trays and lid',
 'outer_mm':[L,W,H],'capacity':8,'parts':checks,
 'keeper_roof_above_tray_mm':ROOF_Z,'pcb_guide_opening_mm':[134.,31.6],
 'pcb_reference_thickness_range_mm':[1.17,1.37],
 'pcb_vertical_play_range_mm':[.13,.33],
 'minimum_component_gap_at_vertical_stop_mm':.2,
 'minimum_component_gap_at_width_stop_mm':.1,
 'reference_module_travel_cases':cases,'assembly_intersections':False,
 'pcb_six_direction_stop_checks':stop_checks,'single_slot_coupon_cases':coupon_cases,
 'screw_intersections':False,'max_installed_screw_lengths_mm':{'keeper':5,'tie':20},
 'blank_short_edge_assumption_mm':2.,
 'fasteners_added':{'M2x5_countersunk':12,'M2x20_countersunk':2},
 'original_four_M2_lid_screws_reused':True,
 'physical_tested':False,'sliced':False,'transport_certified':False,
 'thread_strength_verified':False,'exact_samsung_component_layout_verified':False,
 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.models.glob('*.stl')},
}
(OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Optional pre-arranged upgrade plates. No new exterior body is printed.
def placed(name,x,y,rotate=False):
    mesh=trimesh.load_mesh(OUT/(name+'.stl'))
    if rotate:mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,0,1]))
    mesh.apply_translation(-mesh.bounds[0]+np.array([x,y,0]))
    return mesh

plate1=[placed('lid-retention',17.8,22.4),placed('tray-bottom-2',172.8,56.4,True)]
plate1 += [placed('keeper-2-print-2' if i<2 else 'keeper-3-print-4',17.8+i*14,132.) for i in range(6)]
plates={
 'upgrade-plate-1-lid-bottom-keepers':plate1,
 'upgrade-plate-2-middle-top':[placed('tray-middle-3',56.4,26.2),placed('tray-top-3',56.4,132.)],
 'first-test-plate':[placed('test-tray-1',56.4,85),placed('test-keeper-1-print-2',80,135),placed('test-keeper-1-print-2',150,135)],
}
plate_reports=[]
for name,meshes in plates.items():
    for i,mesh in enumerate(meshes):
        assert mesh.bounds[0,:2].min()>=8-1e-4 and mesh.bounds[1,:2].max()<=248+1e-4
        assert abs(mesh.bounds[0,2])<1e-5
        for other in meshes[:i]:
            gap=np.maximum(0,np.maximum(mesh.bounds[0,:2]-other.bounds[1,:2],other.bounds[0,:2]-mesh.bounds[1,:2]))
            assert np.linalg.norm(gap)>=8-1e-4
    packed=trimesh.util.concatenate(meshes)
    packed.export(OUT/(name+'.stl'))
    reread=trimesh.load_mesh(OUT/(name+'.stl'))
    assert reread.is_watertight and reread.is_winding_consistent
    assert np.allclose(reread.bounds,packed.bounds,atol=2e-5)
    plate_reports.append({'file':name+'.stl','part_count':len(meshes),'bounds_mm':packed.bounds.tolist(),'minimum_part_gap_mm':8})
(OUT/'plate-verification.json').write_text(json.dumps(plate_reports,indent=2),encoding='utf-8')
from retention_preview import preview
preview(OUT,parts,assembled,screws,meshof,box,opposite,plates)
print(json.dumps({'parts':len(parts),'reference_module_travel_cases':cases,'outer_mm':[L,W,H]},indent=2))
