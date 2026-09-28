"""Parametric RDIMM storage prototype; units mm. Python 3.12+.
Install: python -m pip install -r requirements.txt
Run from repository root: python src/build_case.py
No threads are printed: mounting pilots require 6-32 UNC finishing.
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
BASE=4.4; TRAY_FLOOR=.6; SLOT_Z=6.0; PITCH=TRAY_FLOOR+SLOT_Z
BODY_H=BASE+3*PITCH; LID_T=H-BODY_H
SLOT_L,SLOT_W=134.4,31.8
BOARD_L_MAX,BOARD_W_MAX,PCB_T_MAX,COMPONENT_T_MAX=133.8,31.4,1.37,2.1
SLOT_X=(L-SLOT_L)/2
TRAY_X=SLOT_X-1.75; TRAY_L=SLOT_L+3.5
SIDE_X=[28.4988,70.104,130.0988]
BOTTOM_X=[41.275,85.725]; BOTTOM_Y=[3.175,98.425]
LID_X=[3.0,L-3.0]; LID_Y=[10.0,W-10.0]
MOUNT_PILOT=2.7; MOUNT_BORE_DEPTH=3.7
assert LID_T>=1.79, 'Changed slot depth no longer fits the 26 mm envelope'

def box(size,pos=(0,0,0)):return m.Manifold.cube(size).translate(pos)
def cyl(h,r,pos=(0,0,0),rot=(0,0,0),r2=-1):
 return m.Manifold.cylinder(h,r,r2,circular_segments=64).rotate(rot).translate(pos)
def meshof(s):
 q=s.to_mesh();return trimesh.Trimesh(vertices=np.asarray(q.vert_properties)[:,:3],faces=np.asarray(q.tri_verts),process=True)
def layout(n):
 ow=n*SLOT_W+(n-1)*.6+1.2
 oy=(W-ow)/2
 return ow,oy,[oy+.6+i*(SLOT_W+.6) for i in range(n)]

def body():
 a=box((L,W,BODY_H))-box((L-3.2,W-3.2,BODY_H+1),(1.6,1.6,BASE))
 for x in SIDE_X:
  for y in (0,W-6):a+=box((9,6,9.5),(x-4.5,y,0))
 for x in LID_X:
  for y in LID_Y:a+=box((6,6,BODY_H),(x-3,y-3,0))
 ow,oy,_=layout(2)
 for y in (oy-1.2,oy+ow+.4):a+=box((8,.8,3.8),(L/2-4,y,BASE))
 for x in SIDE_X:
  a-=cyl(MOUNT_BORE_DEPTH+.1,MOUNT_PILOT/2,(x,-.1,6.35),(-90,0,0))
  a-=cyl(MOUNT_BORE_DEPTH+.1,MOUNT_PILOT/2,(x,W+.1,6.35),(90,0,0))
 for x in BOTTOM_X:
  for y in BOTTOM_Y:a-=cyl(MOUNT_BORE_DEPTH+.1,MOUNT_PILOT/2,(x,y,-.1))
 for x in LID_X:
  for y in LID_Y:a-=cyl(8.1,.8,(x,y,BODY_H-8))
 return a

def tray(n):
 ow,oy,ys=layout(n)
 a=box((TRAY_L,ow,PITCH),(TRAY_X,oy,0))
 for y in ys:
  a-=box((SLOT_L,SLOT_W,SLOT_Z+.2),(SLOT_X,y,TRAY_FLOOR))
  # Blank short PCB edges rest on shelves. Components clear the tray floor.
  for x in (SLOT_X,SLOT_X+SLOT_L-1.6):a+=box((1.6,SLOT_W,2.2),(x,y,TRAY_FLOOR))
 # Four reliefs clear lid posts without entering the RAM cavities.
 for x in LID_X:
  for y in LID_Y:a-=box((6.5,6.6,PITCH+2),(x-3.25,y-3.3,-1))
 # Grip ribs in the unused end clearances.
 for x in (2.1,L-4.75):a+=box((2.65,10,4.8),(x,W/2-5,0))
 return a

def lid():
 a=box((L,W,LID_T))
 # 0.3 mm stack tolerance above trays; leave perimeter and screw pads intact.
 recess=box((L-3.6,W-3.6,.4),(1.8,1.8,-.1))
 for x in LID_X:
  for y in LID_Y:recess-=box((6,6,1),(x-3,y-3,-.2))
 a-=recess
 for x in LID_X:
  for y in LID_Y:
   a-=cyl(LID_T+.2,1.1,(x,y,-.1))
   a-=cyl(1.05,1.1,(x,y,LID_T-1.05),r2=2.15)
 return a

parts={'body':body(),'tray-2-slots-print-1':tray(2),'tray-3-slots-print-2':tray(3),'lid':lid(),'fit-coupon-1-slot':tray(1)}
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

assembled=[parts['body'],parts['tray-2-slots-print-1'].translate((0,0,BASE)),parts['tray-3-slots-print-2'].translate((0,0,BASE+PITCH)),parts['tray-3-slots-print-2'].translate((0,0,BASE+2*PITCH)),parts['lid'].translate((0,0,BODY_H))]
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
  pcb=box((BOARD_L_MAX,BOARD_W_MAX,PCB_T_MAX),(bx,by,z+2.8))
  # Drawing does not establish an exact Samsung part placement; this is a
  # reference test block with 2 mm blank PCB short edges at both ends.
  comp=box((BOARD_L_MAX-4,BOARD_W_MAX,2*COMPONENT_T_MAX+PCB_T_MAX),(bx+2,by,z+.7))
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

verification={'outer_mm':[L,W,H],'capacity':8,'cavity_mm':[SLOT_L,SLOT_W,SLOT_Z],'parts':checks,'assembly_intersections':False,'reference_module_intersections':False,'reference_module_max_thickness_mm':5.57,'blank_short_edge_assumption_mm':2.0,'mount_screw_penetration_test_mm':3.0,'mount_thread_finishing_required':'6-32 UNC','physical_tested':False,'sliced_in_bambu_studio':False,'exact_samsung_component_placement_verified':False}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf8')

# Mesh-derived preview with back-face culling.
im=Image.new('RGB',(1400,1000),(245,247,250));draw=ImageDraw.Draw(im)
fontpath=args.font
font=ImageFont.truetype(str(fontpath),28) if fontpath else ImageFont.load_default(size=28)
small=ImageFont.truetype(str(fontpath),21) if fontpath else ImageFont.load_default(size=21)
def label(zh,en):return zh if fontpath else en
draw.text((36,24),label('RDIMM 8 条收纳盒 · 标准硬盘外形原型','8-RDIMM storage case - HDD form factor prototype'),font=font,fill=(20,37,57))
draw.text((36,70),label('147 × 101.6 × 26 mm  |  每槽 134.4 × 31.8 × 6.0 mm  |  底部与两侧安装孔','147 x 101.6 x 26 mm | Slots: 134.4 x 31.8 x 6.0 mm | Bottom + side mounts'),font=small,fill=(66,81,99))
transform=np.array([[.78,-.63,0],[.33,.41,-.85],[.535,.665,.519]])
def render(items,cx,cy,scale):
 pixels=np.asarray(im).copy();depth=np.full((im.height,im.width),-np.inf)
 for solid,color in items:
  mm=meshof(solid);vertices=mm.vertices-np.array([L/2,W/2,0]);pp=vertices@transform.T
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
draw.text((40,900),label('安装孔为攻牙底孔；需要后加工 6-32 UNC。4 颗 M2 沉头螺钉固定上盖。','Mounting pilots require 6-32 UNC tapping. Lid: four M2 countersunk screws.'),font=small,fill=(66,81,99))
draw.text((40,940),label('几何检查已通过；未实物试装。托盘短边托住 PCB，避让双面颗粒。','Geometry checked; physical fit untested. Shelves support short PCB edges.'),font=small,fill=(66,81,99))
im.save(OUT/'case-preview.png')
print(json.dumps(verification,ensure_ascii=False,indent=2))
