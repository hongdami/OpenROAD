# Final SKY130HD layout

Copied from one completed run. The flow still writes the live copies under gitignored `work/`.

| File | What it is |
| --- | --- |
| `6_final.gds` | Final GDS. Open it in KLayout. GitHub cannot display it. |
| `6_final.odb` | OpenROAD database. Open it with `scripts/run_systolic2x2.sh --gui` after placing this file where that target expects it, or load it from OpenROAD. |
| `6_final.def` | Placed and routed DEF. |
| `6_final.v` | Final Verilog netlist. |
| `6_final.sdc` | Final constraints. |
| `6_final.spef` | Extracted parasitics. |
| `6_final.cdl` | CDL netlist used for LVS. |
| `6_lvs.lvsdb` | KLayout LVS database. |
