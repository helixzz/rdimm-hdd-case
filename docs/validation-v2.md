# V2 physical validation record

Status: **user print reported; carrying retention needs correction**. The user confirmed printing the v2 two-plate files and described the overall result as good, with noticeable movement during carrying. It is not yet known whether the tray stack, the modules, or both are moving. No measured tolerances or detailed material/slicer information were supplied. Numerical results in `models/v2/verification.json` remain the original generation-time record.

An unprinted [v2-R retrofit](retention.zh-CN.md) is proposed. It has a [separate physical validation record](validation-retention.md).

| Check | Status | Evidence / conditions |
|---|---|---|
| P2S slicing and continuous thin-wall paths | Print reported; path details unknown | Actual slicer/profile/material/nozzle/layer height were not supplied |
| Exact Samsung short PCB-edge contact areas | Not tested | Confirm no components or label buildup on shelves |
| Single-slot component clearance and removal | Not tested | Record module part number and actual print |
| Three-coupon stack without preload | Not tested | Record gap, warp and any witness marks |
| Full 2+3+3 stack with lid resting naturally | Not tested | Do not force the lid down with screws |
| Lid locators and flush countersunk screws | Not tested | Record head size, length and effective tapped depth |
| Side insert calibration and installation | Not tested | Record part, measured bore, material and installation method |
| Repeated side insert tightening / pullout | Not tested | Establish a test method before claiming strength |
| Bottom plastic thread depth and durability | Not tested | Empty body test first; max intrusion 3 mm |
| Chassis/tray fit | Not tested | Record chassis or holder and mounting direction |
| RAM/tray retention during carrying | Issue reported by user | Noticeable movement; source not isolated; v2 has no independent PCB latch |
| Pull eye / optional ribbon usability | Not tested | Keep attachments outside RAM cavities |
| ESD material / enclosure performance | Not tested | No ESD certification implied |

Add dated observations with the exact commit, printer, material and module identification. Keep failures and limitations visible. Do not replace “not tested” solely because the generator or CI passes.
