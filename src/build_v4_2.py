"""V4.2: replace the first upper-tray clip's 0.2 mm root web with a full anchor."""
import argparse
import json
from pathlib import Path
import build_v4_1_rc4 as previous

base=previous.base
v=previous.v
m=previous.m
VERSION='4.2'
ROOT_SHIFT=2.8


def modify(p,fixed,leaves):
    p,fixed,leaves=previous.modify(p,fixed,leaves)
    for name in ('tray-middle-3','tray-top-3'):
        y,old=leaves[name][0]
        new_y=round(y+ROOT_SHIFT,6)
        # Keep the tooth/paddle in the proven PCB position. Only shorten the
        # root end of the beam, and rebuild its R1 transition at the new root.
        leaf=old-v.box((7.,20.,7.),(139.,new_y-20.,-.1))
        fillet=v.box((1.01,1.,6.2),(142.99,new_y,0))
        fillet-=v.cyl(6.4,1.,(144.,new_y+1.,-.1))
        leaf+=fillet
        # Pillar ends at Y14; retain 0.3 mm assembly clearance. This anchor
        # spans the end rail outside the PCB edge (X<=140.5).
        anchor=v.box((4.3,3.,6.2),(140.8,new_y-3.,0))
        fixed[name]+=anchor
        leaves[name][0]=(new_y,leaf)
        p[name]=fixed[name]
        for _,s in leaves[name]:p[name]+=s
        p[name]=p[name].set_tolerance(.001)
    # Recess only the fixed end-frame ledge below each tooth by 0.5 mm.
    # Keep the PCB seat at Z3 and the entire moving tooth unchanged.
    for name in ('body-pin-clearance','body-thread-pilot','tray-middle-3','tray-top-3'):
        z=4. if name.startswith('body') else 0.
        for i,(y,leaf) in enumerate(leaves[name]):
            tooth_y=y-ROOT_SHIFT if name.startswith('tray') and i==0 else y
            relief=v.box((.62,5.2,.51),(140.49,tooth_y+13.4,z+3.9))
            base.clear(relief,leaf,'tooth unchanged by frame relief')
            fixed[name]-=relief
            p[name]-=relief
        p[name]=p[name].set_tolerance(.001)
    return p,fixed,leaves


def configure():
    previous.configure();base.VERSION=VERSION;base.PART_MODIFIER=modify
    import build_v4_1
    build_v4_1.BELT_ENABLED=False
    base.FLOOR_FILLET_RADIUS=6.


def build(out):
    configure();base.build(out,lid_up_probe=.55)
    new,fixed,leaves=base.parts()
    previous.configure();old,oldfixed,oldleaves=base.parts()
    changes={}
    for name,s in new.items():
        add=(s-old[name]).volume();remove=(old[name]-s).volume()
        if name.startswith('lid'):assert add<.001 and remove<.001,(name,add,remove)
        changes[name]={'added_mm3':add,'removed_mm3':remove}
    clearance=[]
    for name in ('body-pin-clearance','body-thread-pilot','tray-middle-3','tray-top-3'):
        z=4. if name.startswith('body') else 0.
        for i,(y,leaf) in enumerate(leaves[name]):
            old_y,old_leaf=oldleaves[name][i]
            region=v.box((6.,5.,2.),(139.,old_y+13.5,z+4.4))
            head=leaf^region
            assert ((old_leaf^region)-head).volume()<.001 and (head-(old_leaf^region)).volume()<.001
            old_hit=((old_leaf^region).translate((0,0,-.3))^oldfixed[name]).volume()
            assert old_hit>.2,('reproduce close frame',name,i,old_hit)
            base.clear(head.translate((0,0,-.65)),fixed[name],('tooth down clearance',name,i))
            # Removing the shelf below the tooth must not alter PCB support height.
            low=v.box((6.,5.,z+3.8),(139.,old_y+13.5,0))
            assert (((oldfixed[name]-fixed[name])^low).volume())<.001,('PCB seat preserved',name,i)
            if name!='body-thread-pilot':
                clearance.append({'part':name,'clip':i+1,'tooth_y':old_y,'frame_recess_depth_mm':.5,
                    'nominal_gap_mm':[.2,.7],'downward_probe_mm':.65,'old_0_3mm_probe_intersection_mm3':old_hit})
    roots=[]
    for name in ('tray-middle-3','tray-top-3'):
        for i,(y,s) in enumerate(leaves[name]):
            # A real solid anchor, not merely manifold connectivity. Demand a
            # 1.0 mm longitudinal x >=0.8 mm transverse x 6.0 mm root-side core.
            width=1. if i==0 else .8
            core=v.box((width,1.,6.),(142.,y-1.,.1))
            missing=(core-fixed[name]).volume()
            assert missing<.001,('missing root core',name,i,missing)
            if i==0:
                assert (v.box((1.,3.,6.),(142.,y-3.,.1))-fixed[name]).volume()<.001,'3 mm anchor core'
            # Require the same full-height core to cross the actual root joint.
            bridge=v.box((width,.2,6.),(142.,y-.1,.1))
            assert (bridge-new[name]).volume()<.001,('root bridge',name,i)
            old_y,old_s=oldleaves[name][i]
            old_core=v.box((width,1.,6.),(142.,old_y-1.,.1))
            old_missing=(old_core-oldfixed[name]).volume()
            if i==0:assert old_missing>4.,old_missing
            # Preserve the complete tooth/paddle rather than only its bounds.
            keeper=v.box((8.,6.,7.),(138.,old_y+13.,0))
            assert ((s^keeper)-(old_s^keeper)).volume()<.001
            assert ((old_s^keeper)-(s^keeper)).volume()<.001
            roots.append({'part':name,'clip':i+1,'old_root_y':old_y,'root_y':y,
                'core_mm':[width,1.,6.],'missing_core_mm3':missing,'old_missing_core_mm3':old_missing})
    (out/'tray-root-fix.json').write_text(json.dumps({'version':VERSION,'baseline':'4.1-rc4',
        'changes':changes,'root_checks':roots,'first_root_web_mm':[.2,3.],
        'tooth_frame_clearance_checks':clearance,
        'floor_transition':{'removed_high_triangular_belt':True,'concave_radius_mm':6.,
            'floor_z_mm':4.,'top_z_mm':10.,'first_removable_tray_z_mm':10.8,
            'tray_vertical_clearance_mm':.8,'mount_voids_preserved':True},
        'first_free_beam_length_mm':[18.,15.2],'tooth_paddle_unchanged':True,
        'old_body_interface_compatible_but_missing_frame_relief':['4.1-rc1','4.1-rc2'],
        'compatible_lid':['4.1-rc3','4.1-rc4'],
        'physical_verified':False,'limits':'Shorter beam may increase release force; no fatigue or impact qualification. Root-core checks supplement connectivity, not a strength calculation.'},indent=2),encoding='utf8')
    configure()
    report=json.loads((out/'verification.json').read_text())
    report['status']='versioned complete release; physical testing pending'
    (out/'verification.json').write_text(json.dumps(report,indent=2))
    print('All six upper clip root cores and tooth preservation checks pass',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.2')
    build(parser.parse_args().output_dir.resolve())
