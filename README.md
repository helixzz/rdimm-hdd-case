# RDIMM HDD Case

3D-printable storage for **8 bare DDR5 RDIMMs** inside a **147 × 101.6 × 26 mm** envelope, with traditional 3.5-inch HDD side and bottom mounting positions.

为服务器内存设计的硬盘位收纳盒：三层托盘，容量 2 + 3 + 3 条，优先保持标准 3.5 寸硬盘外形。目标参考内存为 Samsung M321RAJA0MB2-CCP / CCPKF，打印机参考为 Bambu Lab P2S。

**最新候选：[v4.0-rc4 两条长边 R2 圆角](docs/v4.0-rc4.zh-CN.md)**。在去除侧字的 RC3 基础上，只在长内壁与底板交界增加 R2，并保留安装孔净空；短端卡扣和 SATA 区不变。圆角最高 Z=6，活动托盘最低面 Z=10.8，间距 4.8 mm，完整几何路径和名义刀路检查通过。盖板及托盘与 RC2/RC3 兼容；外壳盘预计增加约 2 秒、0.13 g，整套仍约 3 小时 7 分。改善底部横纹的效果及完整实装尚待验证，当前打印无需中断。

**打印反馈与新候选：[v3.2-rc1 打印可靠性修订](docs/v3.2-rc1.zh-CN.md)**。v3.1 首个外壳出现按压锁扣粘连，暂停按旧方案批量制作。RC 修订锁扣、PCB 槽口，并提供明确支撑配置和一盘可选验证件；完整件仍两盘，既有盖板可保留。[候选几何](models/v3.2-rc1/)需要配套工艺，不能继续无支撑打印；本版仍待实物验证，未覆盖旧 Release。

**检查件实测更新：[RC2 A 底座修正](docs/v3.2-rc2-latch-check.zh-CN.md)**。RC1 小盖板缺少下承托而倾斜掉落，修正件只重打 A 底座，复用原小盖板，参考约 13 分钟。单槽实际 DIMM 装卸无干涉，但固定力偏弱、清理费技巧；完整套件与运输性能仍未验证。RC2 此处仅为检查件修订，不替换整套 RC1 文件。

**当前固定版本：[v3.1 完整两盘实测版](docs/v3.1.zh-CN.md) · [下载 Release](https://github.com/helixzz/rdimm-hdd-case/releases/tag/v3.1)**。v3-S 正式命名为 v3.1，单件几何不变；单套两盘（外壳＋盖板、三个托盘），STL / 3MF 二选一。另有十套共 15 次任务的批量排版与实际参考切片时间。状态仍为待实物验证的预发布，不能把时间估计当作质量保证。[版本规则](docs/versions.zh-CN.md)。

**历史工作名称：[v3-S 一体拨扣托盘](docs/v3-simple.zh-CN.md)，当前请使用 v3.1**。保留 8 条容量和 v3 外壳，取消三片独立限位框，内部只剩三个托盘；每槽插入固定端、拨扣放下、松手固定。新试件仍[一盘完成](models/v3-simple/first-test-all.stl)，整套缩减为两盘。尚未打印验证卡扣力度、耐用性与实际保持能力；请先试单槽件。[查看实际网格预览](models/v3-simple/simple-tray-preview.png)。

**New experimental v3: [免工具取放与固定背板避让](docs/v3.zh-CN.md).** No mandatory internal screws; sliding lid with a release latch, three keyed retainer frames, 2 mm deeper mounting holes, and a connector-end recess. Remains 147 × 101.6 × 26 mm / 8 modules. Print the mechanism/retainer coupons and empty bay-fit gauge first: **v3 has not been physically tested**, and the connector recess does not establish universal backplane compatibility. Closed cover required for inversion retention. Complete [three-plate STL layouts](models/v3) are supplied; v2 and v2-R remain unchanged and must not be mixed with v3.

V3 now includes [engraved operation guides](models/v3/operation-guides.png): `1 PRESS`, `2 OPEN`, `KEEP LEVEL`, matching layer numbers, `LIFT` at the thick end bars, and `SATA END`. These are shallow recesses in the printable geometry, with no external font dependency; the assembly interfaces remain compatible with the earlier unmarked v3.

**V3 首次试打只需一盘：[first-test-all.stl](models/v3/first-test-all.stl)**。空壳、单槽托盘与框、滑轨及锁扣小样共 7 件已排好位置，[查看排版](models/v3/first-test-all.png)。保持 100% 比例，按层打印；需按说明设置局部支撑并检查细筋。无需再分别打印三组试件。

**Status: engineering prototype. A user printed v2 and reported noticeable movement when carrying it.** The experimental [v2-R retention retrofit](docs/retention.zh-CN.md) adds a screwed tray stack and PCB-edge keepers while reusing the v2 body; **the retrofit is not yet physically tested**. This is not a certified ESD or transport enclosure. V2 offers either plastic mounting pilots or optional metal inserts on the six side holes; bottom and lid pilots still require tapping.

![Mesh-derived assembly preview](models/v2/case-preview.png)

**V2 prototype:** greater component-to-floor clearance, lid locating collars, tray pull eyes and tier marks, plus optional side inserts. See [changes and tradeoffs](CHANGELOG.md) and the [detail preview](models/v2/v2-details.png). Do not mix v1 and v2 parts.

## Print the current prototype

- **已有 v2 外壳且遇到晃动：[v2-R 固定升级件与小样说明](docs/retention.zh-CN.md)**。先打印 `models/v2-retention/first-test-plate.stl`；需额外 M2 螺丝，不能混用旧托盘。
- **整盘打印：[P2S 两盘排版与导入说明](plates/v2/README.zh-CN.md)**。每盘一个 STL / 3MF，无需逐件摆放；普通攻牙版和侧面嵌件版分别提供替代第一盘。
- Browse [v2 STL files](models/v2), or use GitHub **Code → Download ZIP** on the branch you intend to print. [V1 files](models/v1) remain available as a historical baseline.
- **先阅读：[v2 中文打印与装配说明](docs/v2.zh-CN.md)**。尺寸出处和原始硬盘孔位来源另见 [v1 基准说明](docs/printing.zh-CN.md)。
- Print one `fit-coupon-1-slot-print-3.stl` first, then three total plus `stack-coupon-cap.stl` for stack fitting. If choosing side inserts, also print `side-insert-coupon.stl` before the body.
- Full set: choose **one** of `body-pilot.stl` / `body-side-inserts.stl`; add `tray-bottom-2.stl`, `tray-middle-3.stl`, `tray-top-3.stl`, and `lid.stl`, one each. STL units are mm; use 100% scale. The lid is already exterior-face-down for printing.

HDD mounts use **6-32 UNC**, not M3. The optional metal-side version is dimensioned specifically for **PEM IUTB-632-150** inserts. Bottom holes remain 2.7 mm plastic pilots, now 3.3 mm deep. Limit installed screw intrusion to 3.0 mm and check actual effective thread depth. The lid uses four M2 countersunk screws; its plastic pilots still require tapping. Read the full guide before printing or installing hardware.

## Design basis and limitations

| Item | v2 value |
| --- | --- |
| Assembled envelope | 147 × 101.6 × 26 mm |
| Capacity | 8 RDIMMs; not a proven maximum-density packing |
| Nominal cavity per module | 134.4 × 31.8 × 6.2 mm |
| Reference maximum module envelope | 133.80 × 31.40 × 5.57 mm |
| Nominal component clearance | 0.30 mm below, 0.33 mm to next tray above |
| Mounting positions | 6 side, 4 bottom; traditional HDD pattern |
| PCB contact assumption | 2 mm component-free region at each short edge |

The envelope comes from Micron's DDR5 RDIMM reference drawing, cross-checked against another Samsung double-sided RDIMM drawing. It is **not a measured or verified mechanical drawing for the exact target Samsung part**. Sources and coordinate conventions are recorded in the [design/printing guide](docs/printing.zh-CN.md#设计基准与来源).

Automated checks cover closed meshes, connected parts, both body assemblies, simplified RAM interference, 64 component-offset cases, insert envelopes, the coupon stack, and 3 mm screw penetration. They do not establish print tolerances, tapping strength, exact component placement, chassis compatibility, or ESD performance. There is no independent PCB latch: arbitrary-orientation retention and transport safety are not established. Ordinary PETG/ASA is not inherently static dissipative. Physical work remains explicitly tracked in the [v2 validation record](docs/validation-v2.md). A 38 mm upright variant is a future design direction; chassis clearance must be established before adopting it.

## Rebuild on another computer

Use **Python 3.12** and Git on Windows, macOS, or Linux. From the repository root:

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux instead:
# source .venv/bin/activate
python -m pip install -r requirements.txt
python src/build_case.py
```

The v2 generator writes nine STL files, `verification.json`, and two mesh-derived PNG previews to ignored `build/`. Geometric assertions run as part of generation; do **not** run Python with `-O`. To choose another directory, pass `--output-dir PATH`. The default preview labels are English; for Chinese labels supply `--font PATH_TO_CHINESE_FONT` (font not bundled).

The design parameters currently live near the top of `src/build_case.py`. Changing dimensions requires reviewing the construction and checks, not just editing a single number. Commit source changes and intentionally regenerated `models/v2/` artifacts together; normal rebuilds leave the tracked baseline untouched. To refresh the v2 baseline, use `python src/build_case.py --output-dir models/v2`. Rebuild the untouched v1 design with `python src/build_v1.py --output-dir build/v1`. GitHub Actions rebuilds both versions on Windows and Linux and uploads the generated files.

## Collaborating

See [CONTRIBUTING.md](CONTRIBUTING.md) for the edit/build/review workflow and [AGENTS.md](AGENTS.md) for agent handoff constraints. Open an issue for print feedback or design proposals. Include module part number, material, nozzle/layer settings, measurements, and photos when available. Share changes in a branch and pull request so work from different computers can be reviewed together.

## License

Original source, CAD/model files, previews, and documentation in this repository are provided under the [MIT License](LICENSE). Referenced manufacturer drawings are linked as design references, are not redistributed here, and retain their respective owners' rights. No manufacturer endorsement or universal fit certification is implied.
