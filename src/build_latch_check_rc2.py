"""RC2 A-coupon correction only; not a new complete enclosure release.

Reuse the printed RC1 slider. Add lower rails missing from the coupon.
"""
from pathlib import Path
import argparse
import json
import hashlib
import zipfile
import numpy as np
import trimesh
import manifold3d as m
import build_v3_2 as rc1
from support_removal_guide import render

ROOT = Path(__file__).resolve().parents[1]
v3 = rc1.v3


def pitch(s, degrees, y=1.6):
    return s.translate((0,-y,-24.4)).rotate((degrees,0,0)).translate((0,y,24.4))


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    old = rc1.old_part('latch-test-base')-v3.box((31,1.8,7),(47,0,20))+rc1.leaf()
    slider = rc1.old_part('latch-test-slider')
    # Two continuous lower bearing rails. Top Z=24.2 leaves 0.2 mm below
    # the existing slider. The 45-degree underside grows from the sidewall.
    section = m.CrossSection([[(34.4,23.0),(35.6,24.2),(34.4,24.2)]])
    left = section.extrude(19.2).rotate((90,0,0)).translate((0,21.,0))
    right = left.mirror((1,0,0)).translate((126.,0,0))
    fixed = old-rc1.leaf()+left+right
    revised = old+left+right
    assert (revised^slider).volume() < .0001
    assert len(revised.decompose()) == 1
    # Reproduce the observed failure: rear of RC1 lid falls while its front
    # remains supported. A pure downward translation was not enough to catch it.
    failure = []
    for angle in [-.5,-1.,-2.,-3.,-5.]:
        a, b = (pitch(slider,angle)^old).volume(), (pitch(slider,angle)^revised).volume()
        assert a < .0001
        if angle <= -1.: assert b > .001
        failure.append({'pitch_deg':angle,'rc1_intersection_mm3':a,'rc2_intersection_mm3':b})
    assert (pitch(slider,2.,20.8)^revised).volume() > .001
    for x, angle in [(34.8,2.),(91.2,-2.)]:
        moved = slider.translate((-x,0,-24.4)).rotate((0,angle,0)).translate((x,0,24.4))
        assert (moved^revised).volume() > .001
    for delta in [(0,-1,0),(0,1,0),(0,0,.4),(0,0,-.4)]:
        assert (slider.translate(delta)^revised).volume() > .001
    for travel in np.linspace(0,2.5,26):
        leaf = rc1.leaf().warp(lambda p:(p[0],p[1],p[2]-float(travel)*max(0.,min(1.,(p[0]-47.)/30.))**2))
        assert (leaf^fixed).volume() < .0001
    for step in np.linspace(0,23,93):
        assert (slider.translate((0,-float(step),0))^(fixed+leaf)).volume() < .0001
    # Distinguish complete case from the cut-down coupon: the full body has
    # separate bearing posts, including rear ones absent from the old coupon.
    body,_ = rc1.revised_body('body-pin-clearance')
    lid = rc1.old_part('lid-slide')
    body_controls = []
    for angle in [-.1,-.5,-1,-2]:
        volume = (pitch(lid,angle)^body).volume()
        assert volume > .001
        body_controls.append({'pitch_deg':angle,'full_body_intersection_mm3':volume})
    mesh = v3.meshof(revised)
    mesh.apply_translation(-mesh.bounds[0])
    mesh.export(out/'latch-test-base.stl')
    restored = trimesh.load_mesh(out/'latch-test-base.stl')
    assert restored.is_watertight and restored.is_winding_consistent
    assert abs(mesh.volume-restored.volume) < .01
    assert np.allclose(mesh.extents,[60,22.6,6.8],atol=.001)
    plate = mesh.copy(); plate.apply_translation([98.,110.,0])
    stem = 'rdimm-3.2-rc2-plate-A-base-only'
    plate.export(out/(stem+'.stl'))
    rc1.write_3mf(out/(stem+'.3mf'),plate)
    with zipfile.ZipFile(out/(stem+'.3mf')) as z:
        data = {n:z.read(n) for n in z.namelist()}
    data['3D/3dmodel.model'] = data['3D/3dmodel.model'].replace(b'RDIMM HDD case v3.2-rc1',b'RDIMM latch check v3.2-rc2')
    with zipfile.ZipFile(out/(stem+'.3mf'),'w',zipfile.ZIP_DEFLATED) as z:
        for n,value in data.items(): z.writestr(n,value)
    crop=v3.box((70,1,9),(30,10,18))
    render([(v3.meshof(old^crop),(72,139,180)),(v3.meshof(((left+right)-old)^crop),(222,159,65))],
           [.1,-1,.5],size=(1000,300)).save(out/'lower-rails-preview.png')
    report = {'version':'3.2-rc2','scope':'A coupon base ONLY; full enclosure and trays remain RC1',
              'reuse_slider':'v3.2-rc1 latch-test-slider', 'lower_rail_top_z':24.2,'nominal_lid_bottom_z':24.4,
              'lower_clearance_mm':.2,'lower_rail_underside_degrees':45,
              'failure_controls':failure,'full_body_controls':body_controls,
              'release_poses':26,'slide_poses':93,'physical_tested':False,
              'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*') if p.suffix in ['.stl','.3mf']}}
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=ROOT/'build/v3.2-rc2-latch-check')
    build(p.parse_args().output_dir)
