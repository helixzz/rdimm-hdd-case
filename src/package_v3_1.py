"""Package immutable v3.1 delivery assets from a clean committed checkout."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(out):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    assert not git('status', '--porcelain'), 'Commit source and artifacts before packaging'
    commit = git('rev-parse', 'HEAD')
    models = ROOT/'models/v3.1'
    manifest = json.loads((models/'release-manifest.json').read_text())
    assert (ROOT/'VERSION').read_text().strip() == manifest['version'] == '3.1'
    for p in manifest['plates']:
        for f in p['files'].values():
            assert hashlib.sha256((models/f['file']).read_bytes()).hexdigest() == f['sha256']
    for report, key in [('bambu-import-stl.json', 'source_stl'), ('bambu-import-3mf.json', 'source_3mf')]:
        for r in json.loads((models/report).read_text())['checks']:
            assert hashlib.sha256((models/r[key]).read_bytes()).hexdigest() == r['source_sha256']
    for r in json.loads((models/'slicing-benchmark.json').read_text())['results']:
        assert hashlib.sha256((models/r['source']).read_bytes()).hexdigest() == r['sha256']
    out.mkdir(parents=True, exist_ok=True)
    packs = [('complete-pin-clearance', [0, 2], '每盘打印一次，共两盘、五件、一套盒子。'),
             ('complete-thread-pilot', [1, 2], '每盘打印一次，共两盘。第一盘为需攻 6-32 UNC 牙的底孔版，不是定位销光孔版。'),
             ('batch-10-pin-clearance', [3, 4], 'A 盘打印 10 次，B 盘打印 5 次，共 15 次任务、10 套。请先完成首套实测。')]
    archives = {}
    for name, indices, instructions in packs:
        chosen = [manifest['plates'][i] for i in indices]
        files = {}
        for p in chosen:
            for f in p['files'].values():
                files[f['file']] = (models/f['file']).read_bytes()
        preview = 'v3.1-batch-10.png' if name.startswith('batch') else 'v3.1-full-plates.png'
        files[preview] = (models/preview).read_bytes()
        files['release-manifest.json'] = (models/'release-manifest.json').read_bytes()
        files['slicing-benchmark.json'] = (models/'slicing-benchmark.json').read_bytes()
        files['validation-v3.1.md'] = (ROOT/'docs/validation-v3.1.md').read_bytes()
        details = '\n'.join('- '+p['plate']+'：'+', '.join(p['parts']) for p in chosen)
        readme = f'''# RDIMM HDD Case v3.1

{instructions}

{details}

每盘的 STL / 3MF 二选一，不要同时导入同一盘的两个格式。3MF 仅有已排好的几何，不含打印机、耗材、支撑预设或 G-code。

选择 P2S / 实际喷嘴和耗材，100% 比例、保持现有方向、按层打印。外壳锁扣下方需局部支撑；检查托盘槽口和扣齿悬挑，并保持拨扣贯通缝可活动。批量 B 盘只有 4 mm 零件间距和 5.5 mm 床边余量，检查裙边与支撑不越界。

清理支撑，先空盒试盖板、托盘和背板，再用真实 DIMM 逐槽试装；不要强推。取放时先拿出托盘，拨开小扣再放下 / 抬起 DIMM。无需独立限位框或内部螺丝。

这些是待实物验证的原型。参考切片成功不等于已验证卡扣力度、质量或实际打印时长。耗材温度选实际 PLA Basic / PLA Pure 配置。先做一套完整验证，再决定十套批量。

固定源代码提交：{commit}

完整说明：https://github.com/helixzz/rdimm-hdd-case/blob/v3.1/docs/v3.1.zh-CN.md

版本：v3.1。保持本包文件与 SHA256SUMS.txt 一起保存；反馈请填写随附实测表。
'''
        files['READ_ME_FIRST.zh-CN.md'] = readme.encode('utf-8')
        files['BUILD.json'] = json.dumps({'version': '3.1', 'tag': 'v3.1', 'commit': commit,
                                          'package': name, 'plates': [p['plate'] for p in chosen]}, indent=2).encode()
        files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(data).hexdigest()+'  '+n+'\n' for n, data in sorted(files.items())).encode()
        path = out/('rdimm-v3.1-'+name+'.zip')
        with zipfile.ZipFile(path, 'w') as z:
            for n, data in sorted(files.items()):
                entry = zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(entry, data)
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            for line in z.read('SHA256SUMS.txt').decode().splitlines():
                digest, n = line.split('  ', 1)
                assert hashlib.sha256(z.read(n)).hexdigest() == digest
        archives[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'SHA256SUMS.txt').write_text(''.join(h+'  '+n+'\n' for n, h in sorted(archives.items())), encoding='utf-8')
    print(json.dumps({'version': '3.1', 'commit': commit, 'archives': archives}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/releases/v3.1')
    args = parser.parse_args()
    package(args.output_dir.resolve())
