"""One-plate A/B support-removal experiment, not production replacement trays."""
import json
import numpy as np
import trimesh
import build_v4_3 as design
from operation_marks import lettering,top_cut

VERSION='4.4-rc1-support-trial'
ROOT=design.base.ROOT
v=design.v


def relieved(fixed,leaf,sy,tooth_y,z=0):
    # Preserve 1.2 mm wide end bearing lands. Recess only the middle ceiling
    # and seat by 0.3 mm; no overall increase of the PCB's retained height.
    for x,dx,y,dy in [(6.49,1.42,sy+13.2,5.6),(139.39,1.12,tooth_y+14.8,2.4)]:
        roof=v.box((dx,dy,.31),(x,y,z+4.59))
        floor=v.box((dx,dy,.31),(x,y,z+2.69))
        fixed-=roof+floor;leaf-=roof
    return fixed,leaf


def pull_supports():
    out=[]
    for a,b in [(14.85,18.15),(18.75,22.05)]:
        s=v.box((6.35,b-a,1.2),(6.65,a,3.2))
        s+=v.box((4.7,b-a,2.41),(8.3,a,.8))
        out.append(s)
    a,b=28.35,32.65
    s=v.box((6.55,b-a,1.2),(133.8,a,3.2))
    s+=v.box((4.7,b-a,2.41),(133.8,a,.8))
    out.append(s)
    return out


def parts():
    design.configure();p,f,l=design.base.parts()
    sy=2.5;root,leaf=l['tray-middle-3'][0];tooth_y=14.5
    crop=v.box((147.,33.6,7.),(0,1.9,0))
    fixed=f['tray-middle-3']^crop
    # Close the cropped divider with the same width/height as the outside rim.
    fixed+=v.box((143.2,.6,6.8),(1.9,34.3,0))
    result={};rows=[]
    for name in ('A','B'):
        ff,ll=(fixed,leaf) if name=='A' else relieved(fixed,leaf,sy,tooth_y)
        model=ff+ll
        # Mark a rigid end bar away from the PCB contact and the spring root.
        model-=top_cut(lettering(name).rotate(90).translate((5.5,4.)),6.8)
        model=model.set_tolerance(.001).simplify(.001)
        supports=pull_supports()
        for i,s in enumerate(supports):
            design.base.clear(model,s,('support separation',name,i))
            # Each grip can translate into the empty module bay without trapping.
            for distance in np.linspace(0,8,33):
                dx=distance if i<2 else -distance
                design.base.clear(model,s.translate((float(dx),0,0)),('support extraction',name,i,distance))
        # Actual reference DIMM extremes + insertion tilt, then +X withdrawal.
        for length in (133.2,133.8):
            for thick in (1.17,1.37):
                ram=design.base.rc.simple.module(length,31.4,thick,6.55,2.7)
                design.base.clear(model,ram,('module',name,length,thick))
                opened=ff+design.base.rc.simple.bend(ll,root)
                for a in np.linspace(0,2,21):
                    design.base.clear(opened,design.base.rc.tilt(ram,6.55,float(a)),('tilt',name,a))
                for dx in np.linspace(0,2,21):
                    design.base.clear(opened,design.base.rc.tilt(ram,6.55,2.).translate((float(dx),0,0)),('withdraw',name,dx))
        # Upward stop remains with the thinnest board at its highest valid pose.
        pcb=v.box((133.8,31.4,1.17),(6.55,2.7,3.73))
        assert (pcb^model).volume()>.01,('missing retention',name)
        for obj in [model]+supports:
            mesh=v.meshof(obj);assert mesh.is_watertight and mesh.is_winding_consistent
            assert len(obj.decompose())==1
        result[name]=(model,supports)
        rows.append({'name':name,'support_count':3,'grip_pull_mm_tested':8,'support_extract_poses':99,
            'root_y':root,'pcb_seat_z_mm':3,'roof_z_mm':4.6,'relieved_middle_depth_mm':.3 if name=='B' else 0,
            'physical_removal_verified':False})
    return result,rows


def main(out=None):
    out=out or ROOT/f'models/v{VERSION}';out.mkdir(parents=True,exist_ok=True)
    result,rows=parts();meshes=[];records=[]
    for name,(model,supports) in result.items():
        t=np.array([54.5,25. if name=='A' else 80.,0.])
        for kind,items in [('keep',[model]),('remove',supports)]:
            for i,s in enumerate(items):
                mesh=v.meshof(s);mesh.apply_translation(t);meshes.append(mesh)
                records.append({'coupon':name,'kind':kind,'index':i,'translation':t.tolist(),'bounds':mesh.bounds.tolist()})
        v.meshof(model).export(out/f'{name}-cleaned-reference-NOT-PRINT.stl')
    combined=trimesh.util.concatenate(meshes)
    stem=f'rdimm-{VERSION}-plate-0-support-ab'
    combined.export(out/(stem+'.stl'));design.base.rc.export_geometry(out/(stem+'.3mf'),combined)
    (out/'verification.json').write_text(json.dumps({'version':VERSION,'scope':'two full-length single-slot test coupons, not replacement production trays',
        'baseline':'4.3','rows':rows,'parts':records,'manual_support_top_gap_mm':.2,'manual_support_bottom_gap_mm':.2,
        'auto_support_needed_for_paddle':True,'configured_project_required':True,'physical_verified':False},indent=2))
    print(out)


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path)
    main(parser.parse_args().output_dir)
