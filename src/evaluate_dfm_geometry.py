"""Design-for-manufacture studies; no changes to released production snapshots."""
import json
import numpy as np
import build_v4_3 as design
import build_dual_trial_v4_4_rc3 as dual

ROOT=design.base.ROOT;v=design.v;base=design.base
OUT=ROOT/'build/dfm-study'

def paddle_gusset(tooth_y,z=0):
    # Extend inside the old paddle so the union is volumetric.
    return base.rc.wedge([(142.8,3.9),(144.3,5.4),(144.3,5.6),(142.8,5.6)],tooth_y+13.6,4.8).translate((0,0,z))

def relieved(fixed,leaf,sy,ty,z):
    # Cut through the exact old seat/roof instead of leaving a coplanar skin.
    for x,dx,y,dy in [(6.49,1.42,sy+13.2,5.6),(139.39,1.12,ty+14.8,2.4)]:
        roof=v.box((dx,dy,.32),(x,y,z+4.59))
        floor=v.box((dx,dy,.32),(x,y,z+2.69))
        fixed-=roof+floor;leaf-=roof
    return fixed,leaf

def altered_parts(p,fixed,leaves,paddle=False,relief=False):
    for name in ('body-pin-clearance','body-thread-pilot','tray-middle-3','tray-top-3'):
        z=4. if name.startswith('body') else 0.
        count=2 if name.startswith('body') else 3
        for i,(y,leaf) in enumerate(leaves[name]):
            ty=y-2.8 if count==3 and i==0 else y
            if paddle:
                extra=paddle_gusset(ty,z)
                leaf+=extra;p[name]+=extra
            if relief:
                sy=v.layout(count)[2][i]
                fixed[name],leaf=relieved(fixed[name],leaf,sy,ty,z)
                p[name],_=relieved(p[name],leaf,sy,ty,z)
            leaves[name][i]=(y,leaf)
        p[name]=p[name].set_tolerance(.001).simplify(.001)
    return p,fixed,leaves

def full_geometry(paddle=False,relief=False):
    design.configure();p,f,l=base.parts()
    return altered_parts(p,f,l,paddle,relief)

def raised_cores():
    cores=[]
    for i,(y,w) in enumerate(((14.85,3.3),(18.75,3.3),(28.35,4.3))):
        x,dx=(6.65,1.25) if i<2 else (139.4,.95)
        s=v.box((dx,w,.8),(x,y,3.4))
        pts=[(7.75,3.4),(10.95,6.6),(9.65,6.6),(7.75,4.2)]
        if i==2: pts=[(147.3-x,z) for x,z in reversed(pts)]
        s+=base.rc.wedge(pts,y,w)
        cores.append(s.set_tolerance(.001).simplify(.001))
    return cores

def specimens(kind):
    q=dual.parts();a=q[0]
    if kind in ('paddle','combined'):a['model']=(a['model']+paddle_gusset(14.5)).set_tolerance(.001).simplify(.001)
    if kind in ('raised-grips','combined'):
        a['cores']=raised_cores()
        a['interfaces']=[s for i,s in enumerate(a['interfaces']) if i%3!=2]
        for i,s in enumerate(a['cores']):
            for cap in a['interfaces']:s-=cap
            a['cores'][i]=s.set_tolerance(.001).simplify(.001)
    return q

def check_specimens(q):
    checks={'core_extraction_poses':0,'volume_overlap':0,'single_connected_parts':0}
    for part in q:
        allparts=[part['model']]+part['cores']+part['interfaces']
        for s in allparts:
            mesh=v.meshof(s)
            assert mesh.is_watertight and mesh.is_winding_consistent and len(s.decompose())==1,part['name']
            checks['single_connected_parts']+=1
        for i,s in enumerate(allparts):
            for t in allparts[:i]:base.clear(s,t,(part['name'],'overlap'))
        for i,s in enumerate(part['cores']):
            for dx in np.linspace(0,8,33):
                x=-dx if part['name']=='A' and i==2 else dx
                base.clear(s.translate((float(x),0,0)),part['model'],(part['name'],'extract',i,dx))
                checks['core_extraction_poses']+=1
    return checks

def access_study():
    rows=[]
    for q in dual.parts():
        if q['kind']!='capture':continue
        core=q['cores'][0];keep=q['model'];center=2+q['capture_length']/2
        # Illustrative rigid peel after interface detachment, NOT adhesion FEA.
        rotations=[]
        for angle in np.arange(0,21,1):
            moved=core.translate((-6.3,0,-3.4)).rotate((0,-float(angle),0)).translate((6.3,0,3.4))
            rotations.append({'angle_deg':int(angle),'intersection_mm3':(moved^keep).volume()})
        tool=v.box((5.,1.,1.),(8.,center-.5,3.8))
        base.clear(tool,keep,(q['name'],'blade approach'))
        base.clear(tool,core,(q['name'],'blade approach to grip'))
        rows.append(dict(name=q['name'],illustrative_blade_clearance_mm=[5,1,1],
                         tool_box_min_mm=[8,center-.5,3.8],rigid_peel=rotations,
                         limitations='Interface fracture, grip deformation and release force not modeled.'))
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True);design.configure();old,_,_=base.parts();report={}
    for name,paddle,relief in [('paddle',True,False),('relief',False,True),('paddle-relief',True,True)]:
        try:
            p,f,l=full_geometry(paddle,relief)
            checks=base.verify(p,f,l,lid_up_probe=.55)
            changes={n:dict(added_mm3=(p[n]-old[n]).volume(),removed_mm3=(old[n]-p[n]).volume()) for n in p}
            report[name]=dict(passed=True,checks=checks,changes=changes)
        except AssertionError as e:report[name]=dict(passed=False,reason=str(e))
        print(name,report[name],flush=True)
    for name in ('paddle','raised-grips','combined'):
        try:report[name+'-coupons']=dict(passed=True,checks=check_specimens(specimens(name)))
        except AssertionError as e:report[name+'-coupons']=dict(passed=False,reason=str(e))
        print(name+'-coupons',report[name+'-coupons'],flush=True)
    report['capture_access']=access_study()
    report['limits']='Rigid CAD/illustrative flexure geometry, not force, fatigue, adhesion, impact, thermal warpage or surface finish simulation.'
    report['baseline']='v4.3 production geometry / v4.4 RC3 material coupons; original mount diameters retained for controlled comparisons'
    (OUT/'geometry.json').write_text(json.dumps(report,indent=2))
    assert all(row['passed'] for row in report.values() if isinstance(row,dict) and 'passed' in row),report

if __name__=='__main__':main()
