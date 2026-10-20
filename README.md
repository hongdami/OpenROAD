# OpenROAD systolic array physical-design example

This project is a physical implementation (Yosys + OpenROAD-flow-scripts),
not an AI functional simulator. The design is a four-PE signed 8-bit 2×2
systolic array with signed 24-bit accumulators, on SKY130HD, with a 10.0 ns
clock (`examples/systolic2x2/constraint.sdc`).

## Prerequisites

- Docker, with the pinned image already present locally. The image name is
  the single line in `toolchain/orfs-image.txt`.
- The `OpenROAD-flow-scripts/` checkout. It is listed in `.gitignore`.
  `scripts/orfs_container.sh` expects `$ORFS_ROOT/flow/Makefile`, and
  `ORFS_ROOT` defaults to `OpenROAD-flow-scripts` in this repository. The
  scripts commit for that checkout is the single line in
  `toolchain/orfs-commit.txt`.
- At least 20 GiB free on the filesystem that holds this project.

Run this first. It checks `docker`, the daemon, both pin files, free space,
and that the pinned image exists locally, then records Yosys, OpenROAD, and
KLayout versions in `work/toolchain-versions.txt`:

```sh
scripts/check_environment.sh
```

## Run

```sh
scripts/check_environment.sh
scripts/run_gcd_baseline.sh
scripts/run_systolic2x2.sh
```

`scripts/run_gcd_baseline.sh` runs the official ORFS SKY130HD GCD design.
It is a toolchain, DRC, and LVS gate. That official design currently misses
timing at its own clock. The script prints a warning on stderr:

```text
WARNING: GCD baseline timing not met (wns max <value>, tns max <value>); baseline gates toolchain/DRC/LVS only
```

That warning is an upstream property of the GCD example. It is not a failure
of this design. When DRC and LVS pass, the script writes `work/gcd/PASS`.

`scripts/run_systolic2x2.sh` exits 1 with `run scripts/run_gcd_baseline.sh first`
unless `work/gcd/PASS` exists. With no arguments it runs ORFS `all`, `drc`,
and `lvs`, requires a non-empty `6_final.spef`, requires DRC count 0, an LVS
netlist match, and non-negative final WNS, then writes the summary and
`work/systolic2x2/PASS`. On success it prints:

```text
systolic2x2 flow passed DRC, LVS, and timing checks (educational, not tapeout signoff)
```

The script accepts at most one argument. Any other form prints the following
and exits 2 (`$0` is the path you used to invoke it):

```text
usage: scripts/run_systolic2x2.sh [--clean | --gui]
```

Remove generated stages for this design:

```sh
scripts/run_systolic2x2.sh --clean
```

`--clean` deletes `work/systolic2x2/PASS` and runs ORFS `clean_all` with this
design's `WORK_HOME`. That target removes the stage files under `results/`,
`reports/`, `logs/`, and `objects/`. It leaves `summary.md`, `summary.json`,
and `metadata.json` in `work/systolic2x2/`, and it does not touch `work/gcd/`.

Open the final database in the OpenROAD GUI:

```sh
scripts/run_systolic2x2.sh --gui
```

Run the batch flow first so
`work/systolic2x2/results/sky130hd/systolic2x2/base/6_final.odb` exists.
`--gui` runs ORFS `gui_final`, which opens that database. The host must have
a working X11 `DISPLAY`. `scripts/run_systolic2x2.sh --gui` calls
`scripts/orfs_container.sh --gui`. If `DISPLAY` is unset, that wrapper prints
`DISPLAY is not set` and exits 2 before it starts Docker, so the batch
results stay as they are. When `DISPLAY` is set, the wrapper passes it and
`/tmp/.X11-unix` into the container.

## Outputs

`work/` is gitignored.

Read `work/systolic2x2/summary.md` and `work/systolic2x2/summary.json` first.
`summary.json` `status` is `PASS` only when final GDS is non-empty, the
KLayout DRC count is 0, LVS is `PASS`, `wns_ns` is numeric and non-negative,
and the setup and hold violation counts are not positive. `PASS` is an empty
marker written after that summary.

Results, reports, and logs are under:

```text
work/systolic2x2/results/sky130hd/systolic2x2/base/
work/systolic2x2/reports/sky130hd/systolic2x2/base/
work/systolic2x2/logs/sky130hd/systolic2x2/base/
```

The results directory includes `6_final.gds`, `6_final.odb`, `6_final.def`,
`6_final.spef`, and `6_final.v`, plus `6_final.sdc`, `6_final.cdl`, and
`6_lvs.lvsdb`. ORFS writes `6_final.spef` during the flow; the run requires
that file to be non-empty before it writes `PASS`.

In `summary.json`, `wns_ns` is the `wns max` line from `6_finish.rpt`: ORFS
worst negative slack, clamped to 0 when setup is met. `worst_setup_slack_ns`
is the actual setup slack. A met clock can show `wns_ns` of 0 with a positive
`worst_setup_slack_ns`.

## Input protocol

Ports on `systolic2x2` are `clk`, `reset`, `valid_in`, `start`, `last`,
signed `a_left[15:0]`, signed `b_top[15:0]`, signed 24-bit `c00`, `c01`,
`c10`, `c11`, and `done`.

For one 2×2 product, present two consecutive cycles with `valid_in` high:

- `a_left[7:0]` is row 0 and `a_left[15:8]` is row 1.
- `b_top[7:0]` is column 0 and `b_top[15:8]` is column 1.
- Assert `start` on the first inner-dimension term and `last` on the second.

The RTL registers `a_left[15:8]` and `b_top[15:8]` for one cycle so row 1 and
column 1 meet the wavefront. `done` is assigned from the bottom-right PE's
forwarded valid and last (`v11 && l11`). It pulses when that PE consumes its
local `last` token.

## Interpretation

SKY130HD DRC/LVS is an educational check, not tapeout signoff.

Power is a vectorless ORFS estimate, not AI-workload power. `summary.json`
stores it in watts as `estimated_power_w`. `summary.md` prints the same
quantity in mW and notes "Vectorless ORFS estimate; not workload power."
