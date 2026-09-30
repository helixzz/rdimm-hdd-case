# Changelog

## v4.4-rc3-dual-trial — Support for PLA contact layers

- Address RC2 feedback: A/B still need prying; C grips break before release. One plate with A, long/short C1/C3 captures and selected H32. Keep A permanent contacts unchanged; widen C grips to4.8/3.4 mm and make removable parts solid.
- Five PLA cores,17 explicit Support For PLA contact volumes, individually assigned to material2; automatic paddle-support interfaces also use material2. Use official GFS02 Support For PLA preset, AMS mapping, prime tower and800 mm3 flushing in both directions; no flushing into printed parts/supports. Actual material mixing and release remain unverified.
- P2S .4/.2 reference1h03m43,10 changes,22.86g including flushing/tower. Geometry/extraction checks and all17 actual interface-path audits pass; report bead-contact gaps and preserve correct material identity. H32 holes remain support-free.
- User selected3.2mm from the printed hole candidates; adopt for future complete side/bottom mounting bores. This numbered prerelease contains coupons only; latest complete release stays v4.3, old assets unchanged.

## v4.4-rc2-combined-trial — one plate for all current cleanup changes

- Combine unchanged RC1 A/B DIMM slots, four cropped lid-capture coupons with inward pull supports, four bottom/side-hole coupons (3.1/3.2/3.3/3.6 mm), and two tray corner coupons with obsolete fins AND floor remnants removed. Twelve labeled specimens; ten modeled removable supports.
- Block automatic support only in intended channels and bores; retain A/B paddle supports. Nominal bead checks pass for all twelve specimens, including grip connectivity and eight empty bores.
- Configured P2S .4 / PLA Basic /.2 project, 56m31 /22.57 g, with illustrated removal guide. Physical removal, bridging, screw fit and retention remain pending. This prerelease keeps the complete v4.3 release and historical RC1 unchanged.

## v4.4-rc1-support-trial — one-plate A/B experiment

- Add two full-length single-slot coupons with three inward-pull sacrificial supports each. Retain automatic paddle supports; include a configured P2S project and removal diagram.
- A retains v4.3 slot contacts. B locally recesses seat/ceiling by ~0.3 mm while preserving end bearing lands. B keeper is locally thinner; retention and fatigue require physical checks.
- Geometry and sampled toolpath checks pass, including 198 support extraction poses. P2S reference 31m55 /13.12 g. Removal force, surface quality and actual insertion remain unverified. This prerelease does not replace the complete v4.3 set.


## v4.3 — continuous floor reinforcement with retained ledge

- Preserve the ledge at Z10.4 with R0.4 top edge, and join its inner face to the Z4 floor using a tangent concave R3.5 blend. The first tray remains at Z10.8 with 0.4 mm clearance; this is wall reinforcement, not a tray seat.
- Only bodies change; v4.2 lid and both upper trays are byte-identical. Preserve holes, SATA, module clearance and loading paths; complete two-plate package still provided.
- Include subdivided cylindrical chord vertices in support blockers; final six bores contain zero support. All other support/clearance audits pass. P2S reference 3h10m44, 125.47 g, approximately 13 s above v4.2. Actual strength and finish remain unverified.


## v4.2 — complete release

- Repair first upper-tray clip anchors with 3 mm full-height bases; preserve keeper positions and R1 root blends.
- Recess fixed frame below all eight DIMM heads by 0.5 mm while preserving PCB seats and moving heads. Nominal sliced model gap 0.6 mm; local support interfaces still require removal.
- Replace high long-wall triangular ridges and separate R2 fillets with continuous concave R6 floor transitions. Preserve mounting bores and loading paths; first upper tray has 0.8 mm vertical clearance.
- Complete four-part/two-project release; RC4 lid reusable, shell and trays updated. P2S reference 3h10m31, 125.47 g. Geometry and nominal toolpath checks pass; complete physical fit, force, fatigue and impact remain unverified.


## v4.1-rc3 — replacement lid for tight RC1/RC2 capture slots

- Address reported entry and full-travel jamming with double entry chamfers, small exit chamfers and .2 -> .4 mm upper/lateral gaps. Preserve flat capture and release latch; RC1/RC2 body and trays unchanged.
- Sliding tongue thins 1.4 -> 1.2 mm with full 1.4 mm root; upper riser narrows to 1.2. Flat bearing area decreases to 41.80 mm2. Upward clearance increases; explicit .55 mm stop probe preserves historical defaults. No unchanged-strength claim.
- Full reference geometry and four replacement-lid support regions pass. One configured replacement-lid plate estimated 36m38 /24.25 g. Physical fit, force, fatigue and impact remain unverified.

## v4.1-rc2 — connect upper wall above bottom-release windows

- Add two 45-degree arch roofs with R1 apex in the original 1.6 mm wall footprint; minimum upper link height 4.114 mm. Preserve lower latch/support access and all loading paths. RC1 lid/tray geometry is unchanged and reusable.
- Configured p2 blocks support only on six side bores and the two arch roofs; re-sliced bead checks find no upper-window support, with all 36 required support areas and nine motion corridors passing. Automatic p1 arch supports retained only as an audit control.
- Same-profile total estimate ~3h12m06, +30 seconds and +0.63 g versus RC1-p1. First physical arch finish, access and impact performance remain unverified.

## v4.1-rc1 — flat lid captures and reinforced clip roots

- Replace four short sloped lid captures with 2 mm flat flanges and matching tongues; preserve the press/8 mm slide/lift operation. Adjust all tray end reliefs: matched complete set required.
- Thicken lid/DIMM springs, widen locking teeth and add root fillets. Brace the long walls with low triangular belts while preserving HDD bores and SATA clearance. Central lid skin stays unchanged to preserve component clearance.
- Full reference geometry/motion, optional-screw, watertight mesh and 36 support/nine corridor audits pass. P1 projects retain local side-hole blockers. Supports on new tongues and ledges need removal; provide actual-path diagrams.
- Same-profile total estimate ~3h11m36, +2.9% and +0.94 g versus RC4-p1. Impact, fatigue, opening force and support-removal ease are untested; not a drop rating.

## v4.0-rc4-p1 — local side-bore support blockers

- Preserve RC4 round bores; block support only on six upper cylindrical side-hole surfaces after difficult support-removal feedback. Retain all other support settings.
- Bambu save/reload preserves paint; six hole regions have zero support extrusion, with 28 other support regions and nine corridors passing nominal bead audits. First plate saves about 54 seconds. Physical unsupported-roof quality and pin fit remain untested.
- Deliver configured projects as a separate process revision; STL cannot carry the support paint.

## v4.0-rc4 — R2 long-wall floor fillet candidate

- Add R2 to the two long internal floor edges while preserving original mounting bores. Leave short-end release windows and SATA geometry unchanged; RC2/RC3 lid and upper trays remain compatible.
- Evaluate R1/1.5/2/3 with sampled full-assembly checks; demonstrate why blindly adding a full perimeter ring fills mounting and release voids. R2 top is Z=6, 4.8 mm below the first removable tray.
- Same-process Bambu first-plate estimate increases by 1.52 seconds and 0.127 g. Two plates and nominal support/corridor audit pass. Surface improvement and full physical assembly remain unverified.

## v4.0-rc3 — remove exterior side engravings

- Fill vertical PRESS/arrow and SATA END cuts following the first RC2 body surface report. Preserve horizontal operation marks, all internal geometry, and RC2 lid/upper-tray compatibility. No internal fillet or slicing speed change.
- Geometry differences are confined to the outer 0.3 mm; full assembly/path checks and two-plate slicing/support audit pass. Reference plate 1 saves about 107 seconds. Physical finish improvement and full assembly remain unverified.

## v4.0-rc2 — standard SATA backplane guide-post depth

- Increase the single connector recess from 6.0 to 7.5 mm after checking SATA-IO 3.3 figures 32/40/42. Reproduce the old cavity collision with the 6.76 mm axial envelope. Width, side and height stay unchanged.
- Extend the 0.8 mm isolation wall; reference chip lateral gap is now 0.2 mm and requires physical checking. Lid and upper trays are unchanged from v4 RC1.
- Rebuild full meshes, two plate layouts, reference configured projects and previews; geometry and nominal toolpath audits pass. Full physical fit and retention remain pending.

## v4.0-rc1 — corrected connector side and integrated bottom

- Move the single connector recess from Y=11–58 to Y=43.6–90.6 mm after correcting bottom/end-view interpretation. Preserve its width, mounting datums and published old artifacts.
- Integrate two bottom slots into the body. Expose their release beams through end windows, isolate their feet above the floor and require removable support. Keep two removable three-slot upper trays.
- Replace continuous lid rails with four corner retainers, a notched lid and an 8 mm slide-then-lift operation. Verify loaded upper-tray insertion, in-shell bottom DIMM removal, lid translation/tilting stops and module envelopes.
- Deliver four parts on two comfortably spaced plates. P2S / PLA Basic / 0.20 mm estimate: 127 min body/lid + 62 min upper trays, about 125 g total. No speed increase or ten-set deadline promise.
- Audit 28 supported regions and nine free corridors from actual Bambu toolpaths. Physical support cleanup, full assembly, dock fit, clip strength and transport reliability remain unverified.

## v3.2-rc2 — A coupon correction only

- Record RC1 physical results: all coupon supports removed, shell leaf returns normally, actual DIMM fits without interference, tray retention feels weak. Full-set and transport validation remain pending.
- Reproduce the A slider tipping into its base: the cropped fixture omitted lower side bearings. Full-body bearing posts block the same rigid path, but do not establish physical success.
- Add two lower rails only to the A coupon base, retaining the existing slider. Add pitch/roll regression checks alongside release and sliding sweeps; preserve all RC1 files and settings.
- Provide a one-base P2S / PLA Basic project estimated at 13 minutes / 3.54 g. This is not a new full enclosure release; tray stiffness and support-cleanup improvements remain open.

## v3.2-rc1 — supported printability candidate

- Record a real v3.1 shell latch fusion failure; trays have not yet been physically printed. Keep the v3.1 release immutable and mark this revision as awaiting physical validation.
- Remove the shell's 0.2 mm parallel-guard clearance and widen its release leaf from 0.8 to 1.6 mm. Local support remains required; the changed load path has no force/fatigue validation.
- Raise tray PCB roofs by 0.1 mm to give 1.6 mm nominal slots and add entry chamfers, keeping the PCB shelf above the connector roof. Recheck reference envelopes, module stops and extraction paths; worst upper component headroom is 0.1 mm.
- Generate editable P2S / PLA Basic Bambu projects with explicit normal/snug supports. Audit support paths under the shell leaf, connector recess, bottom tray recess, all eight teeth/hoods and finger paddles. Support removal is still untested.
- Keep the full set at two plates, add a body-only alternate for existing lids, and pack four optional validation pieces onto one plate. Source scripts generate full vendor presets and G-code only in ignored local build output.

## v3.1 — versioned full-validation release

- Name the v3-S integral-latch design v3.1 without changing part geometry. Publish versioned STL and geometry-only 3MF files, manifests/checksums and an immutable release tag; preserve historical designs.
- Prove two flat plates are minimal for a single set by actual projected area (65,847.84 mm² > 65,536 mm²). Supply both shell-hole variants and clear five-part packing lists.
- Add a ten-set batch option: ten body/lid/bottom plates plus five plates with two middle/top pairs, totaling 15 jobs. This is not a global batch minimum proof.
- Benchmark eight actual CLI slices with P2S 0.4 / PLA Basic profiles. Infill-only tuning saves about 3.6% per set; combined batching/tuning estimates 5.7% machine-time savings for ten sets, plus five fewer plate changes. No physical quality or time guarantee; profiles remain candidates.

## v3-S — experimental integral-latch trays

- Keep eight modules and the v3 shell/lid, replacing three loose retainer frames with fixed end slots and integral outward-release tabs on three trays. Retain tool-free daily use; lift the tray out before releasing RAM.
- Check reference-module clearances, six-direction PCB stops, illustrative flexure travel and a held-release tilt/withdrawal path. Force, fatigue, actual printing and physical retention remain unverified.
- Preserve all v3 files. Publish separate `models/v3-simple` files, one combined six-piece test plate, and a two-plate full set. Existing v3 shell/mechanism test parts need not be reprinted.

## v3 — experimental tool-free storage and backplane-clearance design

- Combine all three first-test groups into `first-test-all.stl`: seven pieces on one 256 mm bed, preserving print orientations, with at least 10 mm part gaps and 15 mm bed margins. Keep individual test files for replacements; add a mesh-derived plate preview and Bambu import verification.

- Engrave simple operating instructions directly into the cover, fixed body walls, tray end rails and paired retainer frames: press/open arrows, level icon, layer numbers, lift points and connector-end orientation. Use original 0.55 mm stroke lettering, 0.30 mm recesses and no external font dependency. Regenerate all plates and retainer lettering samples; preserve assembly interfaces and the 26 mm envelope.

- Remove mandatory interior hardware: three trays and three removable keyed PCB-edge retainer frames are captured by a closed sliding cover. Open trays must stay horizontal; they are not independently latching cartridges.
- Add 45-degree slide rails, a press-down anti-slide latch, optional cover reinforcement screws and finger access. Keep the 26 mm CAD height and eight-module capacity.
- Deepen side/bottom bores to 5.7/5.3 mm (+2 mm), with checked 5 mm intrusion. Offer separate thread-pilot and 3.6 mm locating-pin-clearance bodies.
- Add a 6 x 47 x 6.2 mm connector-end bottom recess as a trial clearance envelope, with a matching bottom tray. Actual fixed-backplane compatibility is unverified.
- Add mechanism/retainer first-test plates, a full-footprint empty fit gauge and three complete P2S plates. Local latch support and thin-wall slicing must be checked.
- Validate 512 module poses, 2048 frame-offset cases, 48 PCB stop controls, 64 retainer coupon cases, lid release sweep and both body options. Record a limited parallel-tilt study (6 or 7 modules under the stated assumptions); do not claim a global packing optimum.
- Preserve all previously printed v2 artifacts. No v3 physical, fatigue, impact, ESD or universal-bay-fit claims.

## v2-R — experimental carrying-retention retrofit

- Respond to a user print of v2 with noticeable carrying rattle; preserve the printed body and original v2 meshes.
- Replace trays/lid, add six PCB-edge keeper bars and short-edge guides, and connect the tray stack to the lid with two M2x20 screws. Add twelve M2x5 keeper screws; the existing four lid screws remain in use.
- Retain intentional PCB clearance instead of force-clamping memory. Add 512 reference translation cases, 48 physical-stop negative controls and 64 single-slot cases.
- Supply a first-test plate and two upgrade plates. Real fit, rattle reduction, thread strength and transport performance remain unverified.

## v2 — unprinted engineering prototype

- Keep the 147 × 101.6 × 26 mm envelope, 8-module capacity and mounting coordinates.
- Raise the short-edge shelves and increase tray pitch: nominal component-to-floor clearance improves from 0.10 to 0.30 mm; clearance to the next tray remains 0.33 mm.
- Reduce base/lid thickness and total stack relief to make room; shorten bottom pilot holes to preserve 0.7 mm of material behind them. V1 parts must not be mixed with v2.
- Add two lid locating collars, tray pull eyes and one/two/three tier marks.
- Offer a separate body with six side bores for PEM IUTB-632-150 inserts; retain bottom plastic pilots due to the edge-distance constraint.
- Add a three-tray single-slot stack coupon, flat cap, insert bore calibration coupon, mesh detail preview and physical validation checklist.
- Extend geometry checks to alternate body, maximum insert envelope, coupon stack, assembled envelope and 64 component-offset cases.
- Preserve v1 meshes and source as `src/build_v1.py`. No physical, orientation-retention, insert-strength or ESD claims are added.

## v1 — initial engineering prototype

- Three removable trays (2+3+3 RDIMMs), conventional HDD mounting pilots, M2-fastened lid, single-slot fit coupon and reference geometry checks.
