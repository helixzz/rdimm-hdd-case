"""Paint only upper cylindrical faces of six side bores as Bambu support blockers.

No geometry or global support settings change. Requires a configured, single
mesh/single instance plate-1 project from this repository, in its original pose.
Bambu TriangleSelector serialization: unsplit BLOCKER(2) => 0b1000 => hex '8'.
Reference: BambuStudio Model.hpp and TriangleSelector.cpp (upstream).
"""
import argparse
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from build_v3 import SIDE_X,W

CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
ET.register_namespace('',CORE)
ET.register_namespace('p',PROD)
ET.register_namespace('BambuStudio','http://schemas.bambulab.com/package/2021')


def paint(source,target,arch_windows=False,bore_tolerance=.0003):
    with zipfile.ZipFile(source) as z:data={n:z.read(n) for n in z.namelist()}
    root=ET.fromstring(data['3D/3dmodel.model'])
    items=root.findall(f'{{{CORE}}}build/{{{CORE}}}item')
    components=root.findall(f'.//{{{CORE}}}component')
    assert len(items)==len(components)==1
    t=np.array([float(x) for x in items[0].attrib['transform'].split()])
    assert np.allclose(t[:9],[1,0,0,0,1,0,0,0,1])
    ct=np.array([float(x) for x in components[0].attrib['transform'].split()])
    assert np.allclose(ct,[1,0,0,0,1,0,0,0,1,0,0,0])
    path=components[0].attrib[f'{{{PROD}}}path'].lstrip('/')
    model=ET.fromstring(data[path])
    verts=np.array([[float(e.attrib[k]) for k in ('x','y','z')] for e in model.findall(f'.//{{{CORE}}}vertex')])
    verts+=t[9:]-[54.5,20.,0.]
    counts={f'{x}-{side}':0 for x in SIDE_X for side in ('front','back')}
    if arch_windows:
        counts.update({f'arch-{y}':0 for y in (19.7,55.1)})
    triangles=model.findall(f'.//{{{CORE}}}triangle')
    for tri in triangles:
        q=verts[[int(tri.attrib[k]) for k in ('v1','v2','v3')]]
        normal=np.cross(q[1]-q[0],q[2]-q[0])
        if normal[2]>=-1e-8:continue
        if arch_windows:
            for y in (19.7,55.1):
                # RC2 arch interior only: sloped shoulders and R1 apex.
                # Exclude vertical wall faces, lower latch and lid captures.
                if (np.all(q[:,0]>=145.399) and np.all(q[:,0]<=147.001)
                    and np.all(q[:,1]>=y-.001) and np.all(q[:,1]<=y+19.001)
                    and np.all(q[:,2]>=11.199) and np.all(q[:,2]<=20.287)):
                    tri.set('paint_supports','8');counts[f'arch-{y}']+=1
        for x in SIDE_X:
            radius=np.linalg.norm(q[:,[0,2]]-[x,6.35],axis=1)
            if not np.allclose(radius,1.8,atol=bore_tolerance):continue
            for side,lo,hi in [('front',-.001,5.701),('back',W-5.701,W+.001)]:
                if np.all(q[:,1]>=lo) and np.all(q[:,1]<=hi):
                    assert tri.attrib.get('paint_supports','8')=='8'
                    tri.set('paint_supports','8');counts[f'{x}-{side}']+=1
    assert all(n>=20 for key,n in counts.items() if not key.startswith('arch')),counts
    if arch_windows:assert all(counts[f'arch-{y}']>=18 for y in (19.7,55.1)),counts
    data[path]=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():z.writestr(n,b)
    return counts


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('target',type=Path)
    a=p.parse_args();print(json.dumps(paint(a.source,a.target)))
