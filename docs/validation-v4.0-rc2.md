# v4.0-rc2 validation

Status: geometry and reference Bambu slicing checked. First body printed; surface defects reported. Complete physical RC2 validation pending.

RC1's 6.0 mm cavity missed the standard backplane guide-post reach. SATA 3.3 figures 32/40/42 yield 6.30 mm nominal and 6.76 mm with the listed axial tolerances conservatively added. RC2 provides 7.50 mm; this is a project allowance, not full interface certification.

| Item | RC2 result |
|---|---|
| Guide-post axial reach vs cavity | CAD passed; old 6 mm regression reproduced |
| Reference chip vs extended isolation wall | CAD gap 0.20 mm; actual component clearance pending |
| Reference modules, loading paths, lid stops, holes, envelope | CAD checks passed |
| Two Bambu plates and 28 support / 9 free-corridor checks | Nominal toolpaths passed |
| Body print | First body completed; side lettering and lower wall surface defects reported |
| Upper tray print and support removal | Pending; user preparing plate 2 |
| Body support removal | Pending |
| Empty shell fully seated in dock / fixed backplane | Pending |
| Actual 8 DIMMs and loaded lid operation | Pending |
| Clip strength, repeated handling and transport | Pending |

Prior coupon observations do not validate this complete body. Record actual material, nozzle, layer height, project hash and observations here. User photographs remain private.

## First body feedback — 2026-09-30

The first body was printed. The user reports poor surface quality around the side lettering and at the floor-to-wall transition, and suggests removing the side lettering and considering an internal curved transition later. The supplied photograph also shows horizontal surface variation beyond the letters. This does not establish a single root cause, layer separation, or functional failure. Actual project hash and any slicer overrides were not reported for this print. No user photo is published.

The user is preparing the internal tray plate. Keep the existing RC2 tray project for this first complete assembly; no geometry or process update is required solely by this surface report. Dock seating, DIMM clearance, lid operation and support removal have not yet been reported.

Follow-up candidates, not changes to the frozen RC2 files:

- Remove vertical side-wall lettering in a future revision; retain necessary operation cues on suitable horizontal rigid faces. Compare toolpaths before claiming an improvement.
- Check the height of the long lower-wall line against the floor/solid-layer transition and changes in speed, flow and layer time. A floor-to-wall transition can produce a similar line; see [Prusa's explanation](https://help.prusa3d.com/article/the-benchy-hull-line_124745). This is a hypothesis for this print, not a confirmed diagnosis.
- Evaluate a local internal fillet or chamfer only after checking DIMM, latch, mounting-hole and SATA cavity clearances. A fillet adds material and does not guarantee removal of the exterior line. Preserve the 26 mm envelope and do not consume the already tight reference chip clearance without explicit revalidation.
