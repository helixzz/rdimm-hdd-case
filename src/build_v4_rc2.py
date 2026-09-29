"""V4 RC2: allow the STANDARD backplane guide posts, not just its mating face.

Serial ATA Revision 3.3 Gold, figures 32, 40, 42 / table 6.
Nominal reach past device plug end = 4.90 + 8.15 + 1.70 - 8.45 = 6.30 mm.
Conservative sum of these axial tolerances = .08 + .10 + .08 + .20 = .46.
This excludes chassis/mounting/printing errors; 7.50 is a design allowance,
not a SATA specified cavity dimension or a universal tolerance certification.
"""
import argparse
import json
from pathlib import Path
import build_v4 as base

VERSION='4.0-rc2'
DEPTH=7.5


def configure():
    base.VERSION=VERSION
    base.SATA_DEPTH=DEPTH
    base.SIDE_MARKS=True


def build(out):
    configure()
    base.build(out)
    nominal=4.90+8.15+1.70-8.45
    allowance=.08+.10+.08+.20
    maximum=nominal+allowance
    p,_,_=base.parts()
    old=base.SATA_DEPTH;base.SATA_DEPTH=6.
    old_parts,_,_=base.parts();base.SATA_DEPTH=old
    # End guides are the depth driver; the entire rectangular envelope is a
    # conservative cutter, not a claim that the whole connector fills it.
    probe=base.v3.box((maximum,47,6.2),(0,base.SATA_Y,0))
    assert (old_parts['body-pin-clearance']^probe).volume()>1.
    base.clear(p['body-pin-clearance'],probe,'standard axial reach')
    for name in ('lid-slide-lift','tray-middle-3','tray-top-3'):
        assert (p[name]-old_parts[name]).volume()<.0001
        assert (old_parts[name]-p[name]).volume()<.0001
    # Reference chips begin at X=8.50 in the worst sampled placement. Avoid
    # deepening the cavity without also extending its .8 mm isolation wall.
    wall_inner=DEPTH+.8
    assert wall_inner<8.5
    report={'version':VERSION,'source':'https://sata-io.org/system/files/specifications/SerialATA_Revision_3_3_Gold.pdf',
            'figures':[32,40,42],'table':6,'pdf_pages':[100,110,112],
            'nominal_guide_reach_mm':round(nominal,2),'linear_axial_tolerance_sum_mm':allowance,
            'guide_reach_with_listed_tolerances_mm':round(maximum,2),'cavity_depth_mm':DEPTH,
            'nominal_remaining_depth_allowance_mm':round(DEPTH-maximum,2),
            'isolation_wall_thickness_mm':.8,'wall_inner_x_mm':wall_inner,
            'reference_chip_min_x_mm':8.5,'reference_chip_to_wall_x_gap_mm':round(8.5-wall_inner,2),
            'unchanged_parts':['lid-slide-lift','tray-middle-3','tray-top-3'],
            'limitations':'Does not include extra chassis/mounting/print errors. Not a complete SATA compliance or physical fit test.'}
    (out/'sata-depth-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=base.ROOT/'build/v4.0-rc2')
    build(p.parse_args().output_dir.resolve())
