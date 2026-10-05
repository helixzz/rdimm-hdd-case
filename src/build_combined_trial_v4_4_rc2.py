"""V4.4 RC2: one plate for DIMM supports, mount holes, captures and tray corners."""
import argparse,json,zipfile
from pathlib import Path
import numpy as np
import trimesh
import build_support_trial_v4_4 as ab
import evaluate_capture_pull_supports as capture
import evaluate_tray_corner_fins as corner
from operation_marks import lettering,stroke,GLYPHS,top_cut

VERSION='4.4-rc2-combined-trial'
ROOT=ab.ROOT
v=ab.v
EXTRA={'C':[[(2,3),(.5,3),(0,2.5),(0,.5),(.5,0),(2,0)]],
       'H':[[(0,0),(0,3)],[(2,0),(2,3)],[(0,1.5),(2,1.5)]],
       '4':[[(1.6,0),(1.6,3),(0,1),(2,1)]],
       '6':[[(2,3),(.5,3),(0,2.4),(0,.5),(.5,0),(1.5,0),(2,.5),(2,1),(1.5,1.5),(0,1.5)]]}

def label(text):
    shape=ab.design.m.CrossSection()
    for i,ch in enumerate(text):
        for path in (EXTRA[ch] if ch in EXTRA else GLYPHS[ch]):shape+=stroke(path).translate((3.1*i,0))
    return shape

def hole_coupon(diameter,name):
    # Reproduce 5.7 mm side depth / Z6.35 axis and 5.3 mm bottom depth.
    s=v.box((24,16,4)) + v.box((24,1.6,10.4))
    s+=v.box((9,6.5,10.4),(.5,0,0))+v.box((8,6.35,6.3),(11,0,0))
    r=diameter/2
    s-=v.cyl(5.8,r,(5,-.1,6.35),rot=(-90,0,0))
    s-=v.cyl(.41,r+.3,(5,-.1,6.35),r2=r,rot=(-90,0,0))
    s-=v.cyl(5.4,r,(15,3.175,-.1))
    s-=v.cyl(.41,r+.3,(15,3.175,-.1),r2=r)
    s-=top_cut(label(name).translate((3,10)),4)
    ab.design.base.clear(s,v.cyl(5.3,r,(15,3.175,0)),'bottom depth')
    ab.design.base.clear(s,v.cyl(5.7,r,(5,0,6.35),rot=(-90,0,0)),'side depth')
    return s

def parts():
    specimens=[]
    def add(name,model,supports,translation,kind,**extra):
        for item in [model]+supports:
            assert len(item.decompose())==1,(name,'disconnected')
            mesh=v.meshof(item);assert mesh.is_watertight and mesh.is_winding_consistent,name
        specimens.append({'name':name,'model':model,'supports':supports,'translation':translation,'kind':kind,**extra})
    result,ab_checks=ab.parts()
    for name,dy in [('A',25.),('B',80.)]:
        s,supports=result[name];add(name,s,supports,[54.5,dy,0],'dimm')
    body,pads,capture_checks=capture.parts()
    for i,((y,length),side) in enumerate(( (c,s) for c in capture.CAPTURES for s in ('left','right'))):
        s=body;pad=pads[i]
        if side=='right':
            s=s.mirror((1,0,0)).translate((147,0,0));pad=pad.mirror((1,0,0)).translate((147,0,0))
        crop=v.box((10,length+4,6.001),(0,y-2,19.999))
        s=(s^crop)+v.box((25,length+4,.801),(0,y-2,19.2))
        shift=(0,2-y,-19.2)
        s=s.translate(shift);pad=pad.translate(shift)
        s-=top_cut(label('C'+str(i+1)).translate((14,2)),.8)
        for distance in np.linspace(0,10,51):ab.design.base.clear(s,pad.translate((float(distance),0,0)),('coupon capture pull',i,distance))
        add('C'+str(i+1),s,[pad],[35+40*i,140,0],'capture',capture_length=length,original_side=side,source_shift=list(shift))
    for i,diameter in enumerate((3.1,3.2,3.3,3.6)):
        name='H'+str(round(diameter*10));s=hole_coupon(diameter,name)
        add(name,s,[],[35+40*i,170,0],'mount',diameter=diameter)
    d=ab.design;d.configure();d.base.PART_MODIFIER=corner.modify
    p,f,l=d.base.parts();corner_checks=d.base.verify(p,f,l,lid_up_probe=.55)
    tray=p['tray-middle-3']
    for i in range(2):
        s=tray if i==0 else tray.mirror((1,0,0)).translate((147,0,0))
        s=(s^v.box((16,11.6,7),(0,90,0))).translate((0,-90,0))
        s-=top_cut(label('K'+str(i+1)).scale((.7,.7)).translate((9,2)),.6)
        assert (s^v.box((4.65,.398,4.6),(1.9,4.901,-.1))).volume()<1e-7
        add('K'+str(i+1),s,[],[35+40*i,205,0],'corner')
    d.configure()
    return specimens,{'ab':ab_checks,'capture_full_body':capture_checks,'corner_full_assembly':corner_checks}

def main(out):
    out.mkdir(parents=True,exist_ok=True);specimens,checks=parts();meshes=[];records=[];placed=[]
    for q in specimens:
        name=q['name'];t=np.array(q['translation']);bounds=[]
        for i,item in enumerate([q['model']]+q['supports']):
            mesh=v.meshof(item);mesh.apply_translation(t);meshes.append(mesh);bounds.append(mesh.bounds)
        bbox=np.array(bounds);lo=bbox[:,0].min(0);hi=bbox[:,1].max(0)
        assert np.all(lo>=[5,5,-.002]) and np.all(hi<=[245,245,26]),(name,lo,hi)
        for other,olo,ohi in placed:
            assert np.any(hi[:2]+3<olo[:2]) or np.any(ohi[:2]+3<lo[:2]),('plate spacing',name,other)
        placed.append((name,lo,hi))
        record={k:val for k,val in q.items() if k not in ('model','supports')}
        record.update(support_count=len(q['supports']),bounds=[lo.tolist(),hi.tolist()]);records.append(record)
    combined=trimesh.util.concatenate(meshes);stem=f'rdimm-{VERSION}-plate-0-combined'
    combined.export(out/(stem+'.stl'));ab.design.base.rc.export_geometry(out/(stem+'.3mf'),combined)
    path=out/(stem+'.3mf')
    with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
    for n,b in data.items():
        if n.endswith('.model'):data[n]=b.replace(b'RDIMM HDD case v3.1',('RDIMM HDD case v'+VERSION).encode())
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    (out/'verification.json').write_text(json.dumps({'version':VERSION,'scope':'one plate, twelve test specimens, not replacement production parts','specimens':records,'checks':checks,'manual_support_pieces':10,'physical_verified':False,'plate_bounds':combined.bounds.tolist()},indent=2))
    print(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/f'models/v{VERSION}');main(p.parse_args().output_dir)
