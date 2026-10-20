# systolic2x2 physical-design summary (SKY130HD)

| Metric | Value |
| --- | --- |
| Status | PASS |
| Run command | scripts/run_systolic2x2.sh |
| DRC violations (KLayout) | 0 |
| LVS | PASS |
| Setup WNS / TNS (ns) | 0 / 0 |
| Worst setup / hold slack (ns) | 3.696 / 0.4185 |
| Setup / hold violations | 0 / 0 |
| Min period (ns) / fmax (MHz) | 4.86 / 205.8 |
| Clock skew (ns) | 0.02372 |
| Std cells (synth / final) | 5276 / 6300 |
| Cell area (um^2) | 28964 |
| Core / die area (um^2) | 74696.6 / 76867.6 |
| Utilization (%) | 38.8 |
| Estimated power (mW) | 3.688 |
| Detailed-route DRC errors | 0 |

## Notes

- Power: Vectorless ORFS estimate; not workload power.
- Signoff: SKY130HD DRC/LVS is an educational check, not tapeout signoff.

## Toolchain

```
orfs_scripts_commit=3692473e791a0b006e935f80d59ab1dbe2512a9f
orfs_image=openroad/orfs@sha256:8e0660b8e2d5eff985e78f001660742013aae537fe79e4f3cb2082100c062f6f
OPENROAD: /OpenROAD-flow-scripts/tools/OpenROAD
Yosys 0.68+post (git sha1 UNKNOWN, Release, GNU /usr/local/bin/wrapped-cc/g++ 11.4.0)
unknown 
KLayout 0.30.12
```
