"""Audit actual tool selection at every modeled interface and automatic support."""
import json,math,re,hashlib
import numpy as np
from build_dual_trial_v4_4_rc3 import ROOT,VERSION
from audit_v3_2_toolpaths import select,grid,footprint

def parse_materials(path,excluded_features=('Custom','Prime tower','Flush')):
    x = y = z = e = 0.
    relative_xyz, relative_e = False, True
    feature, width, height = 'Custom', None, None
    out = [];tool=-1;feature_names=[]
    for line in path.read_text(encoding='utf8').splitlines():
        if line.startswith('; FEATURE: '): feature = line.split(': ', 1)[1]
        if line.startswith('; LINE_WIDTH: '): width = float(line.split(': ', 1)[1])
        if line.startswith('; LAYER_HEIGHT: '): height = float(line.split(': ', 1)[1])
        code = line.split(';', 1)[0].strip()
        if not code: continue
        op = code.split()[0]
        if re.fullmatch(r'T[0-9]+',op):tool=int(op[1:])
        d = {k: float(v) for k, v in re.findall(r'([XYZEFIJ])(-?(?:\d+(?:\.\d*)?|\.\d+))', code)}
        if op == 'G90': relative_xyz = False
        if op == 'G91': relative_xyz = True
        if op == 'M82': relative_e = False
        if op == 'M83': relative_e = True
        if op == 'G92':
            x, y, z, e = (d.get(k, old) for k, old in zip('XYZE', [x, y, z, e]))
        if op not in ['G0', 'G1', 'G2', 'G3']: continue
        nx, ny, nz = (old+d.get(k, 0.) if relative_xyz else d.get(k, old) for k, old in zip('XYZ', [x, y, z]))
        de = d.get('E', 0.) if relative_e else d.get('E', e)-e
        e = e+de
        if de > 0 and feature not in excluded_features and (math.hypot(nx-x, ny-y) > .00001 or op in ['G2', 'G3']):
            assert width and height, ('Missing bead metadata', line)
            assert abs(nz-z) < .002, ('Nonplanar deposition unsupported', line)
            points = [(x, y), (nx, ny)]
            if op in ['G2', 'G3']:
                assert 'I' in d or 'J' in d, ('Unsupported arc', line)
                cx, cy = x+d.get('I', 0), y+d.get('J', 0)
                a, b = math.atan2(y-cy, x-cx), math.atan2(ny-cy, nx-cx)
                sweep = ((a-b) if op == 'G2' else (b-a)) % (2*math.pi)
                if sweep < 1e-10: sweep = 2*math.pi
                radius = math.hypot(x-cx, y-cy)
                points = [(cx+radius*math.cos(t), cy+radius*math.sin(t)) for t in np.linspace(a, a+(-sweep if op == 'G2' else sweep), max(2, math.ceil(radius*sweep/.05)+1))]
                points[0], points[-1] = (x, y), (nx, ny)
            for p, q in zip(points, points[1:]):
                out.append([*p, *q, nz, width, height, float(feature.startswith('Support')),tool]);feature_names.append(feature)
        x, y, z = nx, ny, nz
    return np.array(out),feature_names

def main():
    folder=ROOT/f'build/v{VERSION}-projects';path=folder/'0-dual/plate_1.gcode';segs,features=parse_materials(path)
    geometry=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text());caps=[q for q in geometry['volumes'] if q['role']=='interface'];rows=[]
    for cap in caps:
        lo,hi=np.array(cap['bounds']);rect=[lo[0]+.15,lo[1]+.15,hi[0]-.15,hi[1]-.15];xx,yy=grid(rect);local=select(segs,rect)
        inside=local[(local[:,8]==1)&(local[:,4]>lo[2]+.001)&(local[:,4]<=hi[2]+.101)]
        layers=np.unique(inside[:,4]);assert len(layers)>=2,(cap['name'],'missing material layers',layers)
        ilow=np.full(xx.shape,np.inf);ihigh=np.full(xx.shape,-np.inf)
        bottom=np.full(xx.shape,-np.inf);top=np.full(xx.shape,np.inf)
        for q in inside:
            hit=footprint(q[:8],xx,yy);ilow[hit]=np.minimum(ilow[hit],q[4]-q[6]);ihigh[hit]=np.maximum(ihigh[hit],q[4])
        for q in local[local[:,8]==0]:
            hit=footprint(q[:8],xx,yy)
            if q[4]<(lo[2]+hi[2])/2:bottom[hit]=np.maximum(bottom[hit],q[4])
            elif q[4]-q[6]>(lo[2]+hi[2])/2:top[hit]=np.minimum(top[hit],q[4]-q[6])
        covered=np.isfinite(ilow)&np.isfinite(ihigh)&np.isfinite(bottom)&np.isfinite(top)
        interface_coverage=(np.isfinite(ilow)&np.isfinite(ihigh)).mean()
        assert interface_coverage>.98,(cap['name'],'missing dedicated interface',interface_coverage)
        assert covered.mean()>.8,(cap['name'],'opposing PLA coverage',covered.mean())
        lower=ilow[covered]-bottom[covered];upper=top[covered]-ihigh[covered]
        assert lower.min()>-.011 and upper.min()>-.011,(cap['name'],'overlap',lower.min(),upper.min())
        # Rounded beads, seams and the existing sloped entry do not cover the
        # complete rectangular interface. Require a substantial two-sided
        # contact patch; report the non-contact areas instead of hiding them.
        lower_contact=float(np.mean(abs(ilow-bottom)<.011));upper_contact=float(np.mean(abs(top-ihigh)<.011))
        assert lower_contact>.8 and upper_contact>.8,(cap['name'],'missing opposing contact',lower_contact,upper_contact)
        rows.append({'name':cap['name'],'support_material_layer_tops_mm':layers.tolist(),'interface_covered_fraction':float(interface_coverage),'opposing_PLA_covered_fraction':float(covered.mean()),'zero_gap_contact_fractions':[lower_contact,upper_contact],'lower_gap_range_mm':[float(lower.min()),float(lower.max())],'upper_gap_range_mm':[float(upper.min()),float(upper.max())]})
    # Dedicated material may print only modeled interface volumes or actual
    # auto-support. Tower/flush paths were explicitly excluded by the parser.
    unexpected=[]
    for q in segs[(segs[:,8]==1)&(segs[:,7]==0)]:
        point=np.array([(q[0]+q[2])/2,(q[1]+q[3])/2,q[4]-q[6]/2])
        if not any(np.all(point>=np.array(c['bounds'][0])-.11) and np.all(point<=np.array(c['bounds'][1])+.11) for c in caps):unexpected.append(point.tolist())
    assert not unexpected,('support material outside interfaces',unexpected[:5])
    assert {int(q[8]) for q in segs}=={0,1}
    auto=[q for q,f in zip(segs,features) if f=='Support interface'];assert auto and all(q[8]==1 for q in auto)
    # The selected 3.2 mm side/bottom trial holes remain free of support.
    for rect,lo,hi in [([158.4,116.575,161.6,119.775],0,5.31),([148.1,115,151.9,120.7],4.4,8.3)]:
        s=select(segs,rect);s=s[(s[:,7]==1)&(s[:,4]>lo)&(s[:,4]-s[:,6]<hi)];assert len(s)==0
    text=path.read_text(encoding='utf8')
    assert 'M620 S0A' in text and 'M620 S1A' in text and 'M600' not in '\n'.join(l for l in text.splitlines() if not l.startswith(';'))
    report={'version':VERSION,'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'modeled_interfaces':rows,'automatic_support_interface_uses_material_2':True,'dedicated_material_model_paths_outside_interface_volumes':0,'h32_hole_support_segments':0,'ams_tool_changes_present':True,'physical_verified':False,'limits':'Nominal bead placement and material identity; does not model mixing, adhesion, shrinkage, release force or strength.'}
    (folder/'toolpath-audit.json').write_text(json.dumps(report,indent=2));print('Passed',len(rows),'modeled interfaces')

if __name__=='__main__':main()
