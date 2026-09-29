"""Optional Bambu Studio CLI import/export check. This does NOT slice models."""
from pathlib import Path
from zipfile import ZipFile
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import trimesh

CORE = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
PROD = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
ROOT = Path(__file__).resolve().parents[1]


def transform(value):
    a = np.array([float(v) for v in value.split()]) if value else np.array([1,0,0,0,1,0,0,0,1,0,0,0])
    t = np.eye(4)
    t[:3, :3], t[:3, 3] = a[:9].reshape(3, 3).T, a[9:]
    return t


def read_mesh(path):
    with ZipFile(path) as archive:
        cache = {name: ET.fromstring(archive.read(name)) for name in archive.namelist() if name.endswith('.model')}
    def obj(path, oid, mat):
        element = next(o for o in cache[path].iter(CORE+'object') if o.get('id') == oid)
        mesh = element.find(CORE+'mesh')
        if mesh is not None:
            vertices = np.array([[float(v.get(k)) for k in ('x', 'y', 'z')] for v in mesh.find(CORE+'vertices')])
            faces = np.array([[int(t.get(k)) for k in ('v1', 'v2', 'v3')] for t in mesh.find(CORE+'triangles')])
            result = trimesh.Trimesh(vertices, faces, process=True)
            result.apply_transform(mat)
            return [result]
        result = []
        for c in element.find(CORE+'components'):
            result += obj(c.get(PROD+'path', path).lstrip('/'), c.get('objectid'), mat@transform(c.get('transform')))
        return result
    meshes = []
    for item in cache['3D/3dmodel.model'].find(CORE+'build'):
        meshes += obj('3D/3dmodel.model', item.get('objectid'), transform(item.get('transform')))
    return trimesh.util.concatenate(meshes)


def components(mesh):
    # Vertex connectivity is sufficient for these closed, non-touching meshes;
    # avoid requiring optional scipy/networkx graph dependencies.
    parents = list(range(len(mesh.vertices)))
    def root(a):
        while parents[a] != a:
            parents[a] = parents[parents[a]]
            a = parents[a]
        return a
    for a, b, c in mesh.faces:
        parents[root(b)] = root(a)
        parents[root(c)] = root(a)
    return len({root(i) for i in np.unique(mesh.faces)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bambu', type=Path, required=True, help='Installed Bambu Studio executable')
    parser.add_argument('--models', type=Path, default=ROOT/'models/v3')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/v3-bambu-import')
    parser.add_argument('--report', type=Path, default=ROOT/'build/v3-bambu-import/check.json')
    parser.add_argument('--names', nargs='+', help='Optional model basenames for a derived variant')
    args = parser.parse_args()
    folder = args.output_dir.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    reports = []
    names = ('first-test-all', 'first-test-lid-mechanism', 'first-test-retainer', 'empty-fit-gauge-pin',
             'plate-1-body-pin-clearance-lid', 'plate-1-body-thread-pilot-lid', 'plate-2-middle-top', 'plate-3-bottom-frames')
    if args.names:
        names = args.names
    for name in names:
        source = (args.models/(name+'.stl')).resolve()
        exported = folder/(name+'.3mf')
        result = subprocess.run([str(args.bambu.resolve()), '--arrange', '0', '--export-3mf', str(exported), str(source)],
                                cwd=folder, capture_output=True, timeout=60,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        assert result.returncode == 0 and exported.exists(), (name, result.returncode)
        mesh, original = read_mesh(exported), trimesh.load_mesh(source)
        assert mesh.is_watertight and mesh.is_winding_consistent, name
        assert np.allclose(mesh.bounds, original.bounds, atol=.0002), name
        assert abs(mesh.volume-original.volume) < .05, name
        assert components(mesh) == components(original), name
        reports.append({'source_stl': source.name, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                        'closed_after_roundtrip': True, 'component_count': components(mesh),
                        'maximum_bounds_delta_mm': float(np.max(np.abs(mesh.bounds-original.bounds))),
                        'volume_delta_mm3': float(mesh.volume-original.volume)})
        print(name+': passed', flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'application': 'Bambu Studio', 'operation': 'CLI import/export only; not sliced',
                                      'checks': reports}, indent=2), encoding='utf-8')
