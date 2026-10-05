"""RC4: R2 internal floor fillets on long walls only; preserve mounting bores."""
import argparse
import json
from pathlib import Path
import build_v4_rc3 as previous
from build_v4_rc3 import base

VERSION='4.0-rc4'


def configure():
    previous.configure()
    base.VERSION=VERSION
    base.FLOOR_FILLET_RADIUS=2.


def build(out):
    configure()
    base.build(out)
    p,_,_=base.parts()
    base.FLOOR_FILLET_RADIUS=0.
    old,_,_=base.parts()
    base.FLOOR_FILLET_RADIUS=2.
    allowed=base.v3.box((147,2.03,2.03),(0,1.58,3.98))
    allowed+=allowed.mirror((0,1,0)).translate((0,101.6,0))
    changes={}
    for name in p:
        added=p[name]-old[name];removed=old[name]-p[name]
        assert removed.volume()<.0001,(name,'removed material')
        if name.startswith('body'):
            assert added.volume()>1.
            assert (added-allowed).volume()<.0001,(name,'changed outside long-wall floor strips')
        else:assert added.volume()<.0001,(name,'changed compatible part')
        changes[name]={'added_mm3':round(added.volume(),5),'removed_mm3':round(removed.volume(),5)}
    (out/'compatibility.json').write_text(json.dumps({
        'version':VERSION,'baseline':'4.0-rc3','changes':changes,
        'fillet_radius_mm':2.,'fillet_top_z_mm':6.,'upper_tray_min_z_mm':10.8,
        'upper_tray_vertical_gap_mm':4.8,'location':'Two long inner walls; short ends unchanged; original mounting bore voids preserved',
        'unchanged_parts':['lid-slide-lift','tray-middle-3','tray-top-3'],
        'sata_depth_mm':7.5,'physical_finish_improvement_verified':False,
        'limits':'Sampled rigid geometry does not predict thermal deformation, exterior finish or physical strength.'},indent=2),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.0-rc4')
    build(parser.parse_args().output_dir.resolve())
