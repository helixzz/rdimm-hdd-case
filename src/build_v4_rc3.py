"""RC3 fills exterior side engravings only; preserves every assembly interface."""
import argparse
import json
from pathlib import Path
import build_v4 as base

VERSION='4.0-rc3'


def configure():
    base.VERSION=VERSION
    base.SATA_DEPTH=7.5
    base.SIDE_MARKS=False
    base.FLOOR_FILLET_RADIUS=0.
    base.SHELL_LEAF=base.rc.leaf
    base.PART_MODIFIER=None


def build(out):
    configure()
    base.build(out)
    p,_,_=base.parts()
    base.SIDE_MARKS=True
    old,_,_=base.parts()
    base.SIDE_MARKS=False
    external=base.v3.box((147,.301,26))+base.v3.box((.301,101.6,26))
    changes={}
    for name in p:
        added=p[name]-old[name]
        removed=old[name]-p[name]
        assert removed.volume()<.0001,(name,'removed material')
        if name.startswith('body'):
            assert added.volume()>1.,(name,'missing edit')
            assert (added-external).volume()<.0001,(name,'changed functional interior')
        else:
            assert added.volume()<.0001,(name,'changed compatible part')
        changes[name]={'added_mm3':round(added.volume(),5),'removed_mm3':round(removed.volume(),5)}
    # Same standard-derived axial envelope checked in RC2.
    base.clear(p['body-pin-clearance'],base.v3.box((6.76,47,6.2),(0,base.SATA_Y,0)),'SATA guide reach')
    (out/'compatibility.json').write_text(json.dumps({
        'version':VERSION,'baseline':'4.0-rc2','change':'Fill PRESS/arrow and SATA END side engravings only',
        'changes':changes,'unchanged_parts':['lid-slide-lift','tray-middle-3','tray-top-3'],
        'side_marks':False,'internal_fillet_added':False,'sata_depth_mm':7.5,
        'reference_chip_gap_mm':.2,'physical_finish_improvement_verified':False,
        'limits':'Exterior finish, complete assembly and support removal still need physical verification.'},indent=2),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.0-rc3')
    build(parser.parse_args().output_dir.resolve())
