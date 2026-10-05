"""Parametric RDIMM storage v2 prototype; units mm. Python 3.12+.
Install: python -m pip install -r requirements.txt
Run from repository root: python src/build_case.py
Two alternative bodies: all-pilot or side PEM IUTB-632-150 inserts.
Bottom pilots and lid pilots still require tapping. Do not mix v1/v2 parts.
"""
from pathlib import Path
import argparse,json
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'build')
parser.add_argument('--font',type=Path,help='Optional Chinese-capable TrueType/OpenType font for the preview')
args=parser.parse_args()
OUT=args.output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
import manifold3d as m
import trimesh
import numpy as np
from PIL import Image,ImageDraw,ImageFont

L,W,H=147.0,101.6,26.0
BASE=4.0; TRAY_FLOOR=.6; SLOT_Z=6.2; PITCH=TRAY_FLOOR+SLOT_Z
BODY_H=BASE+3*PITCH; LID_T=H-BODY_H
SLOT_L,SLOT_W=134.4,31.8
BOARD_L_MAX,BOARD_W_MAX,PCB_T_MAX,COMPONENT_T_MAX=133.8,31.4,1.37,2.1
SLOT_X=(L-SLOT_L)/2
TRAY_X=SLOT_X-1.75; TRAY_L=SLOT_L+3.5
SIDE_X=[28.4988,70.104,130.0988]
BOTTOM_X=[41.275,85.725]; BOTTOM_Y=[3.175,98.425]
LID_X=[3.0,L-3.0]; LID_Y=[10.0,W-10.0]
MOUNT_PILOT=2.7; SIDE_PILOT_DEPTH=3.7; BOTTOM_PILOT_DEPTH=3.3
SHELF_Z=3.0
LID_RECESS=.2
LOCATORS=[(LID_X[0],LID_Y[0]),(LID_X[1],LID_Y[1])]
LOCATOR_DIAMETER=4.6; SOCKET_DIAMETER=5.2
LOCATOR_LENGTH=.8; SOCKET_DEPTH=1.2
# PEM IUTB-632-150: dimensions in inches converted to mm. See v2 guide.
INSERT_BORE=4.82; INSERT_DEPTH=4.7
INSERT_LENGTH_MAX=.155*25.4
INSERT_DIAMETER_MAX=.219*25.4
COMPONENT_Z=SHELF_Z-COMPONENT_T_MAX
PCB_TOP=SHELF_Z+PCB_T_MAX
COMPONENT_TOP=PCB_TOP+COMPONENT_T_MAX
assert COMPONENT_Z-TRAY_FLOOR >= .30-1e-9
assert PITCH-COMPONENT_TOP >= .33-1e-9
assert BASE-BOTTOM_PILOT_DEPTH >= .7-1e-9
assert LID_T>=1.59, 'Changed slot depth no longer fits the 26 mm envelope'

def box(size,pos=(0,0,0)):return m.Manifold.cube(size).translate(pos)
def cyl(h,r,pos=(0,0,0),rot=(0,0,0),r2=-1):
 return m.Manifold.cylinder(h,r,r2,circular_segments=64).rotate(rot).translate(pos)
def meshof(s):
 q=s.to_mesh();return trimesh.Trimesh(vertices=np.asarray(q.vert_properties)[:,:3],faces=np.asarray(q.tri_verts),process=True)
def layout(n):
 ow=n*SLOT_W+(n-1)*.6+1.2
 oy=(W-ow)/2
 return ow,oy,[oy+.6+i*(SLOT_W+.6) for i in range(n)]

def body(side_inserts=False):
 a=box((L,W,BODY_H))-box((L-3.2,W-3.2,BODY_H+1),(1.6,1.6,BASE))
 for x in SIDE_X:
  for y in (0,W-6):a+=box((9,6,10.4),(x-4.5,y,0))
 for x in LID_X:
  for y in LID_Y:a+=box((6,6,BODY_H),(x-3,y-3,0))
 ow,oy,_=layout(2)
 for y in (oy-1.2,oy+ow+.4):a+=box((8,.8,3.8),(L/2-4,y,BASE))
 for x in SIDE_X:
  a-=cyl((INSERT_DEPTH if side_inserts else SIDE_PILOT_DEPTH)+.1,(INSERT_BORE if side_inserts else MOUNT_PILOT)/2,(x,-.1,6.35),(-90,0,0))
  a-=cyl((INSERT_DEPTH if side_inserts else SIDE_PILOT_DEPTH)+.1,(INSERT_BORE if side_inserts else MOUNT_PILOT)/2,(x,W+.1,6.35),(90,0,0))
 for x in BOTTOM_X:
  for y in BOTTOM_Y:a-=cyl(BOTTOM_PILOT_DEPTH+.1,MOUNT_PILOT/2,(x,y,-.1))
 for x in LID_X:
  for y in LID_Y:a-=cyl(8.1,.8,(x,y,BODY_H-8))
 for x,y in LOCATORS:
  a-=cyl(SOCKET_DEPTH+.1,SOCKET_DIAMETER/2,(x,y,BODY_H-SOCKET_DEPTH))
 return a

def tray(n,tier=0):
 ow,oy,ys=layout(n)
 a=box((TRAY_L,ow,PITCH),(TRAY_X,oy,0))
 for y in ys:
  a-=box((SLOT_L,SLOT_W,SLOT_Z+.2),(SLOT_X,y,TRAY_FLOOR))
  # Blank short PCB edges rest on shelves. Components clear the tray floor.
  for x in (SLOT_X,SLOT_X+SLOT_L-1.6):a+=box((1.6,SLOT_W,SHELF_Z-TRAY_FLOOR),(x,y,TRAY_FLOOR))
 # Four reliefs clear lid posts without entering the RAM cavities.
 for x in LID_X:
  for y in LID_Y:a-=box((6.5,6.6,PITCH+2),(x-3.25,y-3.3,-1))
 # End tabs contain a through-eye for optional 4 mm pull ribbon / fine hook.
 # Keep ribbon tails and knots outside the RAM cavities and below the lid.
 for x in (2.1,L-4.85):
  a+=box((2.75,14,5.8),(x,W/2-7,0))
  a-=box((1.4,6,6.2),(x+.6,W/2-3,-.1))
 # One/two/three recessed ticks identify bottom/middle/top; same marker end.
 for i in range(tier):
  a-=box((1.0,.6,.6),(3.2,W/2+3.6+i*1.2,5.4))
 return a

def lid():
 a=box((L,W,LID_T))
 # 0.2 mm stack tolerance above trays; leave perimeter and screw pads intact.
 recess=box((L-3.6,W-3.6,LID_RECESS+.1),(1.8,1.8,-.1))
 for x in LID_X:
  for y in LID_Y:recess-=box((6,6,1),(x-3,y-3,-.2))
 a-=recess
 # Two diagonal annular spigots register the lid before screws are tightened.
 for x,y in LOCATORS:
  a+=cyl(LOCATOR_LENGTH+.1,LOCATOR_DIAMETER/2,(x,y,-LOCATOR_LENGTH))
 for x in LID_X:
  for y in LID_Y:
   a-=cyl(LID_T+LOCATOR_LENGTH+.2,1.1,(x,y,-LOCATOR_LENGTH-.1))
   a-=cyl(1.05,1.1,(x,y,LID_T-1.05),r2=2.15)
 return a

def stack_cap():
 ow,oy,_=layout(1)
 return box((TRAY_L,ow,1.6),(TRAY_X,oy,0))

def insert_coupon():
 # Same 6 mm side-wall depth / 6.35 mm axis / 10.4 mm boss height as body.
 a=box((40,6,10.4))
 for i,diameter in enumerate((4.82,4.92,5.02)):
  x=7+13*i
  a-=cyl(4.8,diameter/2,(x,-.1,6.35),(-90,0,0))
  for tick in range(i+1):
   a-=box((.7,1.2,.6),(x-1.4+tick*1.1,3.5,9.9))
 return a

parts={'body-pilot':body(), 'body-side-inserts':body(True),
       'tray-bottom-2':tray(2,1), 'tray-middle-3':tray(3,2),
       'tray-top-3':tray(3,3), 'lid':lid(),
       'fit-coupon-1-slot-print-3':tray(1), 'stack-coupon-cap':stack_cap(),
       'side-insert-coupon':insert_coupon()}
checks=[]
for name,s in parts.items():
 mm=meshof(s)
 # Translate each print part to nonnegative coordinates, base z=0.
 printmesh=mm.copy()
 if name=='lid':printmesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
 shift=-printmesh.bounds[0];printmesh.apply_translation(shift)
 path=OUT/(name+'.stl');printmesh.export(path)
 reread=trimesh.load_mesh(path)
 assert reread.is_watertight and reread.is_winding_consistent
 assert len(s.decompose())==1
 checks.append({'part':name,'bbox_mm':reread.extents.tolist(),'volume_cm3':s.volume()/1000,'watertight':True,'one_component':True,'translation_for_print':shift.tolist()})

assembled=[parts['body-pilot'],parts['tray-bottom-2'].translate((0,0,BASE)),
           parts['tray-middle-3'].translate((0,0,BASE+PITCH)),
           parts['tray-top-3'].translate((0,0,BASE+2*PITCH)),
           parts['lid'].translate((0,0,BODY_H))]
for i in range(len(assembled)):
 for j in range(i):
  overlap=(assembled[i]^assembled[j]).volume()
  assert overlap<1e-6,(i,j,overlap)

# Simplified module with maximum component envelope; end keep-outs leave shelves.
modules=[]
for tier,n in enumerate((2,3,3)):
 z=BASE+tier*PITCH
 for y in layout(n)[2]:
  bx=(L-BOARD_L_MAX)/2;by=y+(SLOT_W-BOARD_W_MAX)/2
  pcb=box((BOARD_L_MAX,BOARD_W_MAX,PCB_T_MAX),(bx,by,z+SHELF_Z))
  # Drawing does not establish an exact Samsung part placement; this is a
  # reference test block with 2 mm blank PCB short edges at both ends.
  comp=box((BOARD_L_MAX-4,BOARD_W_MAX,2*COMPONENT_T_MAX+PCB_T_MAX),(bx+2,by,z+COMPONENT_Z))
  mod=pcb+comp
  for p in assembled:assert (p^mod).volume()<1e-6
  modules.append(mod)

# Check the safe 3 mm major-diameter screw penetration stays outside RAM/trays.
probes=[]
for x in SIDE_X:
 probes.extend([cyl(3,1.76,(x,0,6.35),(-90,0,0)),cyl(3,1.76,(x,W,6.35),(90,0,0))])
for x in BOTTOM_X:
 for y in BOTTOM_Y:probes.append(cyl(3,1.76,(x,y,0)))
for q in probes:
 for p in assembled[1:]+modules:assert (q^p).volume()<1e-6

# Check the alternate body, maximum insert envelopes, and a 3-coupon stack.
for part in assembled[1:]+modules:
 assert (parts['body-side-inserts']^part).volume()<1e-6
insert_envelopes=[]
for x in SIDE_X:
 insert_envelopes.extend([
  cyl(INSERT_LENGTH_MAX,INSERT_DIAMETER_MAX/2,(x,0,6.35),(-90,0,0)),
  cyl(INSERT_LENGTH_MAX,INSERT_DIAMETER_MAX/2,(x,W,6.35),(90,0,0))])
for insert in insert_envelopes:
 for part in assembled[1:]+modules:assert (insert^part).volume()<1e-6

# Component tolerance stress check. PCB support contact is intentional and
# excluded; this is NOT an arbitrary orientation / vibration simulation.
# Exercise every corner of x/y +/-0.2 and z +/-0.2 mm translation error.
from itertools import product
stress_cases=0
for tier,n in enumerate((2,3,3)):
 z=BASE+tier*PITCH
 for y in layout(n)[2]:
  bx=(L-BOARD_L_MAX)/2;by=y+(SLOT_W-BOARD_W_MAX)/2
  comp=box((BOARD_L_MAX-4,BOARD_W_MAX,2*COMPONENT_T_MAX+PCB_T_MAX),
           (bx+2,by,z+COMPONENT_Z))
  for delta in product((-.2,.2),repeat=3):
   moved=comp.translate(delta)
   for part in assembled:assert (moved^part).volume()<1e-6
   stress_cases+=1

coupon_stack=[parts['fit-coupon-1-slot-print-3'].translate((0,0,i*PITCH)) for i in range(3)]
coupon_stack.append(parts['stack-coupon-cap'].translate((0,0,3*PITCH)))
for i,a in enumerate(coupon_stack):
 for b in coupon_stack[:i]:assert (a^b).volume()<1e-6
for tier in range(3):
 by=layout(1)[2][0]+(SLOT_W-BOARD_W_MAX)/2
 bx=(L-BOARD_L_MAX)/2;z=tier*PITCH
 mod=box((BOARD_L_MAX,BOARD_W_MAX,PCB_T_MAX),(bx,by,z+SHELF_Z))
 mod+=box((BOARD_L_MAX-4,BOARD_W_MAX,2*COMPONENT_T_MAX+PCB_T_MAX),(bx+2,by,z+COMPONENT_Z))
 for a in coupon_stack:assert (a^mod).volume()<1e-6

# Verify the true assembled envelope including the lid registration spigots.
bounds=np.array([meshof(p).bounds for p in assembled])
assert np.allclose(bounds[:,0,:].min(axis=0),[0,0,0],atol=1e-5)
assert np.allclose(bounds[:,1,:].max(axis=0),[L,W,H],atol=1e-5)
verification={
 'version':'v2','outer_mm':[L,W,H],'capacity':8,
 'cavity_mm':[SLOT_L,SLOT_W,SLOT_Z],'parts':checks,
 'base_mm':BASE,'tray_pitch_mm':PITCH,'lid_nominal_mm':LID_T,
 'component_bottom_clearance_mm':round(COMPONENT_Z-TRAY_FLOOR,3),
 'component_top_clearance_to_next_tray_mm':round(PITCH-COMPONENT_TOP,3),
 'lid_stack_relief_mm':LID_RECESS,
 'assembly_intersections':False,'reference_module_intersections':False,
 'component_translation_stress_mm':.2,'component_translation_stress_cases':stress_cases,
 'alternate_body_intersections':False,'max_insert_envelope_intersections':False,
 'stack_coupon_intersections':False,'reference_module_max_thickness_mm':5.57,
 'blank_short_edge_assumption_mm':2.0,'mount_screw_penetration_test_mm':3.0,
 'side_insert_part':'PEM IUTB-632-150','side_insert_bore_mm':INSERT_BORE,
 'side_insert_depth_mm':INSERT_DEPTH,'bottom_pilot_depth_mm':BOTTOM_PILOT_DEPTH,
 'bottom_thread_finishing_required':'6-32 UNC','lid_thread_finishing_required':'M2',
 'physical_tested':False,'sliced_in_bambu_studio':False,
 'exact_samsung_component_placement_verified':False,
 'arbitrary_orientation_retention_verified':False,
 'heat_set_pullout_strength_verified':False,'esd_verified':False}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf8')

# Mesh-derived preview with back-face culling.
im=Image.new('RGB',(1400,1000),(245,247,250));draw=ImageDraw.Draw(im)
fontpath=args.font
font=ImageFont.truetype(str(fontpath),28) if fontpath else ImageFont.load_default(size=28)
small=ImageFont.truetype(str(fontpath),21) if fontpath else ImageFont.load_default(size=21)
def label(zh,en):return zh if fontpath else en
draw.text((36,24),label('RDIMM v2 · 8 条收纳盒原型','RDIMM v2 - 8-slot HDD form factor prototype'),font=font,fill=(20,37,57))
draw.text((36,70),label('147 × 101.6 × 26 mm  |  每槽 134.4 × 31.8 × 6.2 mm  |  底部与两侧安装孔','147 x 101.6 x 26 mm | Slots: 134.4 x 31.8 x 6.2 mm | Bottom + side mounts'),font=small,fill=(66,81,99))
transform=np.array([[.78,-.63,0],[.33,.41,-.85],[.535,.665,.519]])
def render(items,cx,cy,scale,center=None):
 pixels=np.asarray(im).copy();depth=np.full((im.height,im.width),-np.inf)
 for solid,color in items:
  mm=meshof(solid);vertices=mm.vertices-np.array(center if center is not None else [L/2,W/2,0]);pp=vertices@transform.T
  xy=pp[:,:2]*scale+np.array([cx,cy])
  for i,tri in enumerate(mm.faces):
   nn=mm.face_normals[i]
   if nn@transform[2]<=0:continue
   shade=.74+.22*max(0,float(nn@np.array([-.3,-.4,.866])))
   poly=xy[tri];zz=pp[tri,2]
   xmin=max(0,int(np.floor(poly[:,0].min())));xmax=min(im.width-1,int(np.ceil(poly[:,0].max())))
   ymin=max(0,int(np.floor(poly[:,1].min())));ymax=min(im.height-1,int(np.ceil(poly[:,1].max())))
   if xmin>xmax or ymin>ymax:continue
   xx,yy=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
   (x0,y0),(x1,y1),(x2,y2)=poly
   den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
   if abs(den)<1e-10:continue
   aa=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
   bb=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
   cc=1-aa-bb;z=aa*zz[0]+bb*zz[1]+cc*zz[2]
   target=depth[ymin:ymax+1,xmin:xmax+1]
   hit=(aa>=-1e-7)&(bb>=-1e-7)&(cc>=-1e-7)&(z>target)
   target[hit]=z[hit]
   pixels[ymin:ymax+1,xmin:xmax+1][hit]=(np.array(color)*shade).astype(np.uint8)
 im.paste(Image.fromarray(pixels))
render([(assembled[0],(87,124,151)),(assembled[-1],(98,139,164))],350,355,2.8)
draw.text((40,505),label('闭合外形：26 mm 高','Closed case: 26 mm high'),font=font,fill=(20,37,57))
exploded=[(assembled[0],(87,124,151)),(assembled[1].translate((0,0,35)),(92,145,132)),(assembled[2].translate((0,0,62)),(92,145,132)),(assembled[3].translate((0,0,89)),(92,145,132)),(assembled[4].translate((0,0,117)),(98,139,164))]
render(exploded,1055,675,2.7)
draw.text((745,833),label('底层 2 条 + 中层 3 条 + 顶层 3 条','Tray capacity: 2 + 3 + 3 RDIMMs'),font=font,fill=(20,37,57))
draw.text((40,900),label('v2：两种外壳、盖板定位环、提拉孔、层序标识。请勿混用 v1 零件。','Two body options, lid locators, pull eyes, tier marks. Do not mix v1 parts.'),font=small,fill=(66,81,99))
draw.text((40,940),label('颗粒理论间隙：下方 0.30 mm / 上方 0.33 mm。尚未打印或试装。','Nominal component clearance: 0.30 mm below / 0.33 mm above. Physical fit untested.'),font=small,fill=(66,81,99))
im.save(OUT/'case-preview.png')

# Actual-mesh close-ups make the small v2 changes inspectable.
im=Image.new('RGB',(1400,1050),(245,247,250));draw=ImageDraw.Draw(im)
draw.text((36,25),'V2 details - actual geometry (views use different scales)',font=font,fill=(20,37,57))
tab=parts['tray-top-3']^box((11,20,8),(0,W/2-10,0))
render([(tab,(92,145,132))],330,335,18,center=[5,W/2,0])
draw.text((40,100),'Pull eye + three top-tier marks',font=font,fill=(20,37,57))
draw.text((40,440),'Eye: 1.4 x 6 mm; optional thin pull ribbon.',font=small,fill=(66,81,99))
corner=parts['body-pilot']^box((8,12,5),(0,4,19.8))
lid_corner=(parts['lid']^box((8,12,4),(0,4,-1))).translate((0,0,BODY_H+4))
render([(corner,(87,124,151)),(lid_corner,(98,139,164))],1040,365,19,center=[4,10,20])
draw.text((760,100),'Lid locator + matching socket',font=font,fill=(20,37,57))
draw.text((760,440),'4.6 / 5.2 mm diameters; two diagonal pairs.',font=small,fill=(66,81,99))
coupon=parts['side-insert-coupon'].rotate((0,0,180)).translate((40,6,0))
render([(coupon,(189,142,84))],345,780,10,center=[20,3,0])
draw.text((40,560),'Side-insert calibration coupon',font=font,fill=(20,37,57))
draw.text((40,880),'1 / 2 / 3 marks identify 4.82 / 4.92 / 5.02 mm.',font=small,fill=(66,81,99))
stack_view=[(p.translate((0,0,12*i)),(92,145,132)) for i,p in enumerate(coupon_stack)]
render(stack_view,1050,800,2.4)
draw.text((760,560),'Three-slot stack test (exploded)',font=font,fill=(20,37,57))
draw.text((760,900),'Three identical single-slot trays + flat cap.',font=small,fill=(66,81,99))
draw.text((40,980),'Physical fit, insert strength, orientation retention and ESD remain unverified.',font=small,fill=(66,81,99))
im.save(OUT/'v2-details.png')
print(json.dumps(verification,ensure_ascii=False,indent=2))
