# V2 physical validation record

Status: **not sliced, printed, or physically tested**. Numerical results are in `models/v2/verification.json`; they do not satisfy the physical checks below.

| Check | Status | Evidence / conditions |
|---|---|---|
| P2S slicing and continuous thin-wall paths | Not tested | Record slicer/profile/material/nozzle/layer height |
| Exact Samsung short PCB-edge contact areas | Not tested | Confirm no components or label buildup on shelves |
| Single-slot component clearance and removal | Not tested | Record module part number and actual print |
| Three-coupon stack without preload | Not tested | Record gap, warp and any witness marks |
| Full 2+3+3 stack with lid resting naturally | Not tested | Do not force the lid down with screws |
| Lid locators and flush countersunk screws | Not tested | Record head size, length and effective tapped depth |
| Side insert calibration and installation | Not tested | Record part, measured bore, material and installation method |
| Repeated side insert tightening / pullout | Not tested | Establish a test method before claiming strength |
| Bottom plastic thread depth and durability | Not tested | Empty body test first; max intrusion 3 mm |
| Chassis/tray fit | Not tested | Record chassis or holder and mounting direction |
| RAM retention in intended chassis orientation | Not tested | No independent PCB latch; no transport rating |
| Pull eye / optional ribbon usability | Not tested | Keep attachments outside RAM cavities |
| ESD material / enclosure performance | Not tested | No ESD certification implied |

Add dated observations with the exact commit, printer, material and module identification. Keep failures and limitations visible. Do not replace “not tested” solely because the generator or CI passes.
