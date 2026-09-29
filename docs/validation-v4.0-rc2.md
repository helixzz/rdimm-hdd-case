# v4.0-rc2 validation

Status: geometry and reference Bambu slicing checked; complete physical RC2 validation pending.

RC1's 6.0 mm cavity missed the standard backplane guide-post reach. SATA 3.3 figures 32/40/42 yield 6.30 mm nominal and 6.76 mm with the listed axial tolerances conservatively added. RC2 provides 7.50 mm; this is a project allowance, not full interface certification.

| Item | RC2 result |
|---|---|
| Guide-post axial reach vs cavity | CAD passed; old 6 mm regression reproduced |
| Reference chip vs extended isolation wall | CAD gap 0.20 mm; actual component clearance pending |
| Reference modules, loading paths, lid stops, holes, envelope | CAD checks passed |
| Two Bambu plates and 28 support / 9 free-corridor checks | Nominal toolpaths passed |
| Physical print and support removal | Pending |
| Empty shell fully seated in dock / fixed backplane | Pending |
| Actual 8 DIMMs and loaded lid operation | Pending |
| Clip strength, repeated handling and transport | Pending |

Prior coupon observations do not validate this complete body. Record actual material, nozzle, layer height, project hash and observations here. User photographs remain private.
