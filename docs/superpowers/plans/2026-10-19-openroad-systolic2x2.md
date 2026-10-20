# OpenROAD 2×2 Systolic Array Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible SKY130HD RTL-to-GDSII example for a 2×2 signed systolic array, including reports, GUI data, GDS, DRC, and LVS.

**Architecture:** Keep the existing `OpenROAD/` checkout unchanged. Use a pinned official ORFS container together with a shallow `OpenROAD-flow-scripts/` checkout, mount this project at `/work`, and drive the external design through `DESIGN_CONFIG=/work/examples/systolic2x2/config.mk`. Gate the custom run on a successful official GCD baseline.

**Tech Stack:** SystemVerilog, SDC/Tcl, GNU Make, Docker, Yosys, OpenROAD, KLayout, Bash, Python 3 standard library.

## Global Constraints

- Platform is `sky130hd`.
- Initial clock period is exactly `10.0 ns`.
- Each PE uses signed 8-bit A/B operands and a signed 24-bit accumulator.
- The array has one synchronous-reset clock domain and no SRAM, macros, generated clocks, AXI, DMA, floating point, or quantization logic.
- The first transaction contains two consecutive valid cycles; `start` is asserted on the first and `last` on the second.
- `done` pulses when the bottom-right PE consumes its local `last` token.
- Keep `OpenROAD/` unchanged.
- Treat SKY130HD DRC/LVS as an educational check, not tapeout signoff.
- Treat default ORFS power as a vectorless estimate, not workload power.
- Never convert a DRC, LVS, routing, or timing failure into an unconditional pass.

## Platform amendment — 2026-10-19

SKY130HD supersedes Nangate45 for final implementation. The pinned official
ORFS Nangate45 config references the nonexistent
`platforms/nangate45/lvs/FreePDK45.lylvs`; that failed baseline is retained as
historical diagnostic evidence in `.superpowers/sdd/task-5-report.md`.
SKY130HD supplies an official LVS deck, so the baseline and custom flows keep
the required `all`, `drc`, and `lvs` gates. The custom design uses the
official SKY130HD platform PDN; the former local Nangate45 M1/M4/M7 PDN is
removed.

---

## File structure

| Path | Responsibility |
|---|---|
| `.gitignore` | Exclude nested tool checkouts and generated ORFS output. |
| `toolchain/orfs-image.txt` | Pin the official ORFS image by immutable digest. |
| `toolchain/orfs-commit.txt` | Record the host ORFS flow-script revision. |
| `scripts/orfs_container.sh` | Run one command with the pinned image and both host mounts. |
| `scripts/check_environment.sh` | Validate Docker, mounts, space, image, and tool versions. |
| `scripts/run_gcd_baseline.sh` | Run and gate on the official SKY130HD GCD flow. |
| `scripts/run_systolic2x2.sh` | Run, clean, or open the custom flow. |
| `scripts/check_signoff.sh` | Host-side gate on DRC count, LVS verdict, and (optionally) final timing. |
| `scripts/summarize_results.py` | Convert ORFS metadata and signoff files into JSON/Markdown. |
| `examples/systolic2x2/rtl/processing_element.sv` | One registered signed MAC and wavefront hop. |
| `examples/systolic2x2/rtl/systolic2x2.sv` | Four-PE array, boundary skewing, and completion signal. |
| `examples/systolic2x2/constraint.sdc` | 10 ns clock and I/O timing constraints. |
| `examples/systolic2x2/config.mk` | External ORFS SKY130HD design configuration using the official platform PDN. |
| `tests/yosys/processing_element.ys` | PE elaboration and structural checks. |
| `tests/yosys/systolic2x2.ys` | Array hierarchy, loop, latch, and multiplier checks. |
| `tests/test_project_contract.py` | Fast host-side tests for scripts and configuration. |
| `tests/test_check_signoff.py` | Behavioral tests for `check_signoff.sh` against fake reports. |
| `tests/test_summarize_results.py` | Unit tests for result classification and reporting. |
| `README.md` | User-facing setup, execution, outputs, and limitations. |

### Task 1: Reproducible ORFS container boundary

**Files:**
- Create: `.gitignore`
- Create: `toolchain/orfs-image.txt`
- Create: `toolchain/orfs-commit.txt`
- Create: `scripts/orfs_container.sh`
- Create: `scripts/check_environment.sh`
- Create: `tests/test_project_contract.py`

**Interfaces:**
- Consumes: Docker CLI and the official ORFS Git repository.
- Produces: `scripts/orfs_container.sh [--gui] COMMAND...`; exits with the command status.
- Produces: `work/toolchain-versions.txt` after environment validation.

- [ ] **Step 1: Write the failing host contract test**

```python
# tests/test_project_contract.py
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectContractTest(unittest.TestCase):
    def test_tool_checkouts_and_outputs_are_ignored(self):
        text = (ROOT / ".gitignore").read_text()
        for entry in ("/OpenROAD/", "/OpenROAD-flow-scripts/", "/work/"):
            self.assertIn(entry, text)

    def test_container_wrapper_mounts_project_and_orfs(self):
        text = (ROOT / "scripts/orfs_container.sh").read_text()
        self.assertIn('$PROJECT_ROOT:/work', text)
        self.assertIn(
            '$ORFS_ROOT/flow:/OpenROAD-flow-scripts/flow', text
        )
        self.assertIn("toolchain/orfs-image.txt", text)

    def test_environment_check_records_all_tool_versions(self):
        text = (ROOT / "scripts/check_environment.sh").read_text()
        for tool in ("yosys -V", "openroad -version", "klayout -v"):
            self.assertIn(tool, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm the missing files fail**

Run:

```bash
python3 -m unittest tests.test_project_contract -v
```

Expected: `ERROR` for missing `.gitignore` and scripts.

- [ ] **Step 3: Add ignore rules**

```gitignore
/OpenROAD/
/OpenROAD-flow-scripts/
/work/
__pycache__/
*.pyc
```

- [ ] **Step 4: Fetch ORFS and pin both script and image revisions**

Run:

```bash
git clone --depth 1 https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git
mkdir -p toolchain
git -C OpenROAD-flow-scripts rev-parse HEAD > toolchain/orfs-commit.txt
docker pull openroad/orfs:latest
docker image inspect openroad/orfs:latest \
  --format '{{index .RepoDigests 0}}' > toolchain/orfs-image.txt
test -s toolchain/orfs-commit.txt
rg '^openroad/orfs@sha256:[0-9a-f]{64}$' toolchain/orfs-image.txt
```

Expected: both lock files contain one non-empty line; the image line matches
the digest pattern.

- [ ] **Step 5: Implement the container wrapper**

```bash
#!/usr/bin/env bash
# scripts/orfs_container.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORFS_ROOT="${ORFS_ROOT:-$PROJECT_ROOT/OpenROAD-flow-scripts}"
IMAGE_FILE="$PROJECT_ROOT/toolchain/orfs-image.txt"
GUI=0

if [[ "${1:-}" == "--gui" ]]; then
  GUI=1
  shift
fi

[[ $# -gt 0 ]] || { echo "usage: $0 [--gui] COMMAND..." >&2; exit 2; }
[[ -f "$IMAGE_FILE" ]] || { echo "missing $IMAGE_FILE" >&2; exit 2; }
[[ -f "$ORFS_ROOT/flow/Makefile" ]] || {
  echo "missing ORFS flow at $ORFS_ROOT/flow" >&2
  exit 2
}

IMAGE="$(<"$IMAGE_FILE")"
DOCKER_ARGS=(
  run --rm -i
  --user "$(id -u):$(id -g)"
  -e HOME=/tmp
  -e WORK_HOME=/work
  -v "$PROJECT_ROOT:/work"
  -v "$ORFS_ROOT/flow:/OpenROAD-flow-scripts/flow"
  -w /OpenROAD-flow-scripts/flow
)

if [[ "$GUI" == 1 ]]; then
  [[ -n "${DISPLAY:-}" ]] || { echo "DISPLAY is not set" >&2; exit 2; }
  DOCKER_ARGS+=(
    -e "DISPLAY=$DISPLAY"
    -e QT_X11_NO_MITSHM=1
    -v /tmp/.X11-unix:/tmp/.X11-unix
    --network host
  )
fi

exec docker "${DOCKER_ARGS[@]}" "$IMAGE" \
  bash -lc 'source /OpenROAD-flow-scripts/env.sh; exec "$@"' bash "$@"
```

- [ ] **Step 6: Implement environment validation**

```bash
#!/usr/bin/env bash
# scripts/check_environment.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRED_KIB=$((20 * 1024 * 1024))

command -v docker >/dev/null || { echo "docker is not installed" >&2; exit 1; }
docker info >/dev/null
[[ -s "$PROJECT_ROOT/toolchain/orfs-image.txt" ]]
[[ -s "$PROJECT_ROOT/toolchain/orfs-commit.txt" ]]

AVAILABLE_KIB="$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print $4}')"
if (( AVAILABLE_KIB < REQUIRED_KIB )); then
  echo "at least 20 GiB free space is required" >&2
  exit 1
fi

IMAGE="$(<"$PROJECT_ROOT/toolchain/orfs-image.txt")"
docker image inspect "$IMAGE" >/dev/null
mkdir -p "$PROJECT_ROOT/work"
{
  printf 'orfs_scripts_commit=%s\n' \
    "$(<"$PROJECT_ROOT/toolchain/orfs-commit.txt")"
  printf 'orfs_image=%s\n' "$IMAGE"
  "$PROJECT_ROOT/scripts/orfs_container.sh" bash -c \
    'yosys -V; openroad -version; klayout -v'
} | tee "$PROJECT_ROOT/work/toolchain-versions.txt"
```

- [ ] **Step 7: Make scripts executable and rerun the host tests**

Run:

```bash
chmod +x scripts/orfs_container.sh scripts/check_environment.sh
bash -n scripts/orfs_container.sh scripts/check_environment.sh
python3 -m unittest tests.test_project_contract -v
scripts/check_environment.sh
```

Expected: three unit tests pass; syntax checks return zero; the version file
contains Yosys, OpenROAD, and KLayout version output.

- [ ] **Step 8: Commit the environment boundary**

```bash
git add .gitignore toolchain scripts/orfs_container.sh \
  scripts/check_environment.sh tests/test_project_contract.py
git commit -m "build: pin ORFS container environment"
```

### Task 2: Registered signed processing element

**Files:**
- Create: `tests/yosys/processing_element.ys`
- Create: `examples/systolic2x2/rtl/processing_element.sv`

**Interfaces:**
- Consumes: `clk`, synchronous `reset`, `valid_in`, `start_in`, `last_in`,
  signed `a_in[7:0]`, and signed `b_in[7:0]`.
- Produces: registered A/B and control forwarding plus signed `acc_out[23:0]`.

- [ ] **Step 1: Write the failing Yosys structural test**

```tcl
# tests/yosys/processing_element.ys
read_verilog -sv /work/examples/systolic2x2/rtl/processing_element.sv
hierarchy -check -top processing_element
proc
check -assert
select -assert-count 1 t:$mul
select -assert-count 1 t:$add
stat
```

- [ ] **Step 2: Run it before the RTL exists**

Run:

```bash
scripts/orfs_container.sh yosys -q -s /work/tests/yosys/processing_element.ys
```

Expected: non-zero exit with “No such file or directory”.

- [ ] **Step 3: Implement the PE**

```systemverilog
// examples/systolic2x2/rtl/processing_element.sv
module processing_element (
  input  logic                     clk,
  input  logic                     reset,
  input  logic                     valid_in,
  input  logic                     start_in,
  input  logic                     last_in,
  input  logic signed [7:0]        a_in,
  input  logic signed [7:0]        b_in,
  output logic                     valid_out,
  output logic                     start_out,
  output logic                     last_out,
  output logic signed [7:0]        a_out,
  output logic signed [7:0]        b_out,
  output logic signed [23:0]       acc_out
);
  logic signed [15:0] product;
  logic signed [23:0] extended_product;

  always_comb begin
    product = a_in * b_in;
    extended_product = {{8{product[15]}}, product};
  end

  always_ff @(posedge clk) begin
    if (reset) begin
      valid_out <= 1'b0;
      start_out <= 1'b0;
      last_out <= 1'b0;
      a_out <= '0;
      b_out <= '0;
      acc_out <= '0;
    end else begin
      valid_out <= valid_in;
      start_out <= valid_in && start_in;
      last_out <= valid_in && last_in;
      if (valid_in) begin
        a_out <= a_in;
        b_out <= b_in;
        if (start_in)
          acc_out <= extended_product;
        else
          acc_out <= acc_out + extended_product;
      end
    end
  end
endmodule
```

- [ ] **Step 4: Run structural checks**

Run:

```bash
scripts/orfs_container.sh yosys -q -s /work/tests/yosys/processing_element.ys
```

Expected: zero exit; exactly one `$mul` and one `$add`; no `check` errors.

- [ ] **Step 5: Commit the PE**

```bash
git add examples/systolic2x2/rtl/processing_element.sv \
  tests/yosys/processing_element.ys
git commit -m "feat: add signed systolic processing element"
```

### Task 3: 2×2 systolic array and wavefront alignment

**Files:**
- Create: `tests/yosys/systolic2x2.ys`
- Create: `examples/systolic2x2/rtl/systolic2x2.sv`

**Interfaces:**
- Consumes: packed signed A rows `a_left[15:0]`, B columns `b_top[15:0]`,
  `valid_in`, `start`, `last`, `clk`, and synchronous `reset`.
- Produces: signed `c00`, `c01`, `c10`, `c11` and one-cycle `done`.

- [ ] **Step 1: Write the failing array structural test**

```tcl
# tests/yosys/systolic2x2.ys
read_verilog -sv /work/examples/systolic2x2/rtl/processing_element.sv
read_verilog -sv /work/examples/systolic2x2/rtl/systolic2x2.sv
hierarchy -check -top systolic2x2
select -assert-count 4 t:processing_element
flatten
proc
opt_clean
check -assert
select -assert-min 4 t:$mul
stat
```

- [ ] **Step 2: Run it before the top level exists**

Run:

```bash
scripts/orfs_container.sh yosys -q -s /work/tests/yosys/systolic2x2.ys
```

Expected: non-zero exit naming the missing `systolic2x2.sv`.

- [ ] **Step 3: Implement the array**

```systemverilog
// examples/systolic2x2/rtl/systolic2x2.sv
module systolic2x2 (
  input  logic                      clk,
  input  logic                      reset,
  input  logic                      valid_in,
  input  logic                      start,
  input  logic                      last,
  input  logic signed [15:0]        a_left,
  input  logic signed [15:0]        b_top,
  output logic signed [23:0]        c00,
  output logic signed [23:0]        c01,
  output logic signed [23:0]        c10,
  output logic signed [23:0]        c11,
  output logic                      done
);
  logic signed [7:0] a1_skew, b1_skew;
  logic skew_valid, skew_start, skew_last;

  logic signed [7:0] a00_right, b00_down;
  logic signed [7:0] a01_right, b01_down;
  logic signed [7:0] a10_right, b10_down;
  logic signed [7:0] a11_right, b11_down;
  logic v00, s00, l00, v01, s01, l01;
  logic v10, s10, l10, v11, s11, l11;

  always_ff @(posedge clk) begin
    if (reset) begin
      a1_skew <= '0;
      b1_skew <= '0;
      skew_valid <= 1'b0;
      skew_start <= 1'b0;
      skew_last <= 1'b0;
    end else begin
      skew_valid <= valid_in;
      skew_start <= valid_in && start;
      skew_last <= valid_in && last;
      if (valid_in) begin
        a1_skew <= a_left[15:8];
        b1_skew <= b_top[15:8];
      end
    end
  end

  processing_element pe00 (
    .clk, .reset,
    .valid_in, .start_in(start), .last_in(last),
    .a_in(a_left[7:0]), .b_in(b_top[7:0]),
    .valid_out(v00), .start_out(s00), .last_out(l00),
    .a_out(a00_right), .b_out(b00_down), .acc_out(c00)
  );

  processing_element pe01 (
    .clk, .reset,
    .valid_in(v00), .start_in(s00), .last_in(l00),
    .a_in(a00_right), .b_in(b1_skew),
    .valid_out(v01), .start_out(s01), .last_out(l01),
    .a_out(a01_right), .b_out(b01_down), .acc_out(c01)
  );

  processing_element pe10 (
    .clk, .reset,
    .valid_in(v00), .start_in(s00), .last_in(l00),
    .a_in(a1_skew), .b_in(b00_down),
    .valid_out(v10), .start_out(s10), .last_out(l10),
    .a_out(a10_right), .b_out(b10_down), .acc_out(c10)
  );

  processing_element pe11 (
    .clk, .reset,
    .valid_in(v10), .start_in(s10), .last_in(l10),
    .a_in(a10_right), .b_in(b01_down),
    .valid_out(v11), .start_out(s11), .last_out(l11),
    .a_out(a11_right), .b_out(b11_down), .acc_out(c11)
  );

  assign done = v11 && l11;
endmodule
```

- [ ] **Step 4: Run the hierarchy and arithmetic checks**

Run:

```bash
scripts/orfs_container.sh yosys -q -s /work/tests/yosys/systolic2x2.ys
```

Expected: zero exit; four PE instances before flattening, at least four
multipliers after flattening, and no `check` errors.

- [ ] **Step 5: Commit the array**

```bash
git add examples/systolic2x2/rtl/systolic2x2.sv \
  tests/yosys/systolic2x2.ys
git commit -m "feat: assemble 2x2 systolic array"
```

### Task 4: SKY130HD ORFS design configuration

**Files:**
- Create: `examples/systolic2x2/constraint.sdc`
- Create: `examples/systolic2x2/config.mk`
- Modify: `tests/test_project_contract.py`

**Interfaces:**
- Consumes: RTL from Tasks 2–3 and ORFS's SKY130HD platform files.
- Produces: an external ORFS `DESIGN_CONFIG` with a 10 ns clock and the
  official platform PDN.

- [ ] **Step 1: Add failing configuration assertions**

Add this method to `ProjectContractTest`:

```python
    def test_orfs_configuration_contract(self):
        config = (ROOT / "examples/systolic2x2/config.mk").read_text()
        sdc = (ROOT / "examples/systolic2x2/constraint.sdc").read_text()
        for value in (
            "DESIGN_NAME = systolic2x2",
            "PLATFORM = sky130hd",
            "/work/examples/systolic2x2/rtl/processing_element.sv",
            "/work/examples/systolic2x2/rtl/systolic2x2.sv",
            "CORE_UTILIZATION ?= 35",
        ):
            self.assertIn(value, config)
        self.assertIn("set clk_period 10.0", sdc)
        self.assertIn("create_clock", sdc)
```

- [ ] **Step 2: Confirm the test fails**

Run:

```bash
python3 -m unittest tests.test_project_contract -v
```

Expected: the new method errors because `config.mk` is absent.

- [ ] **Step 3: Add the ORFS design configuration**

```make
# examples/systolic2x2/config.mk
export DESIGN_NAME = systolic2x2
export PLATFORM = sky130hd

export VERILOG_FILES = \
  /work/examples/systolic2x2/rtl/processing_element.sv \
  /work/examples/systolic2x2/rtl/systolic2x2.sv
export SDC_FILE = /work/examples/systolic2x2/constraint.sdc

export CORE_UTILIZATION ?= 35
export PLACE_DENSITY_LB_ADDON = 0.10
export TNS_END_PERCENT = 100
export SYNTH_REPEATABLE_BUILD ?= 1
export ABC_AREA = 1
export ADDER_MAP_FILE :=
```

- [ ] **Step 4: Add the exact 10 ns constraints**

```tcl
# examples/systolic2x2/constraint.sdc
current_design systolic2x2

set clk_name core_clock
set clk_port_name clk
set clk_period 10.0
set clk_io_pct 0.2

set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

set clk_io_name vclk_$clk_name
create_clock -name $clk_io_name -period $clk_period
set_clock_latency 0.2 [get_clocks $clk_name]
set_clock_latency 0.2 [get_clocks $clk_io_name]

set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * $clk_io_pct] \
  -clock $clk_io_name $non_clock_inputs
set_output_delay [expr $clk_period * $clk_io_pct] \
  -clock $clk_io_name [all_outputs]
```

- [ ] **Step 5: Validate configuration and run synthesis only**

Run:

```bash
python3 -m unittest tests.test_project_contract -v
scripts/orfs_container.sh make \
  DESIGN_CONFIG=/work/examples/systolic2x2/config.mk \
  WORK_HOME=/work/work/systolic2x2 synth
test -f work/systolic2x2/results/sky130hd/systolic2x2/base/1_synth.odb
rg -n 'Latch inferred|Warning:.*loop|Module.*not found' \
  work/systolic2x2/logs/sky130hd/systolic2x2/base/1_2_yosys.log \
  && exit 1 || true
```

Expected: all unit tests pass, `1_synth.odb` exists, and the forbidden-pattern
search finds nothing.

- [ ] **Step 6: Commit the physical configuration**

```bash
git add examples/systolic2x2/config.mk \
  examples/systolic2x2/constraint.sdc \
  tests/test_project_contract.py
git commit -m "feat: configure SKY130HD physical flow"
```

### Task 5: Baseline gate and custom flow orchestration

**Files:**
- Create: `scripts/run_gcd_baseline.sh`
- Create: `scripts/run_systolic2x2.sh`
- Create: `scripts/check_signoff.sh`
- Create: `tests/test_check_signoff.py`
- Modify: `tests/test_project_contract.py`

**Interfaces:**
- Produces: `work/gcd/PASS` only after GCD `all`, `drc`, and `lvs` targets
  and a clean `check_signoff.sh` DRC/LVS verdict (timing reported, not
  required; a negative WNS prints an explicit warning).
- Consumes: `work/gcd/PASS` before any custom full run.
- Produces: `work/systolic2x2/PASS` only after custom `all`, `drc`, and `lvs`,
  a non-empty ORFS `6_final.spef`, and `check_signoff.sh --require-timing`.
- Supports: `scripts/run_systolic2x2.sh --clean` (also removes `PASS`) and
  `--gui`; any other argument prints usage and exits 2.
- `scripts/check_signoff.sh [--require-timing] RESULTS_DIR REPORTS_DIR LOGS_DIR`
  fails unless `6_final.gds` is non-empty, `6_drc_count.rpt` is exactly `0`,
  and `6_lvs.log` contains `Congratulations! Netlists match.` without
  `Netlists don't match`; it prints `wns max`/`tns max` from `6_finish.rpt`
  and, with `--require-timing`, fails on missing or negative WNS.

- [ ] **Step 1: Add failing orchestration assertions**

Add this method to `ProjectContractTest`:

```python
    def test_flow_scripts_preserve_stage_failures(self):
        baseline = (ROOT / "scripts/run_gcd_baseline.sh").read_text()
        custom = (ROOT / "scripts/run_systolic2x2.sh").read_text()
        self.assertIn("set -euo pipefail", baseline)
        self.assertIn("set -euo pipefail", custom)
        self.assertLess(baseline.index(" all"), baseline.index(" drc"))
        self.assertLess(baseline.index(" drc"), baseline.index(" lvs"))
        self.assertIn('[[ -f "$PROJECT_ROOT/work/gcd/PASS" ]]', custom)
        self.assertIn("gui_final", custom)
```

- [ ] **Step 2: Confirm the missing scripts fail the test**

Run:

```bash
python3 -m unittest tests.test_project_contract -v
```

Expected: the new method errors on missing run scripts.

- [ ] **Step 3: Implement the GCD baseline gate**

```bash
#!/usr/bin/env bash
# scripts/run_gcd_baseline.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_HOME=/work/work/gcd
CONFIG=/OpenROAD-flow-scripts/flow/designs/sky130hd/gcd/config.mk
STATUS_DIR="$PROJECT_ROOT/work/gcd"
CURRENT_STAGE=preflight

trap 'echo "GCD baseline failed during: $CURRENT_STAGE" >&2' ERR
rm -f "$STATUS_DIR/PASS"
mkdir -p "$STATUS_DIR"

for target in all drc lvs; do
  CURRENT_STAGE="$target"
  "$PROJECT_ROOT/scripts/orfs_container.sh" make \
    "DESIGN_CONFIG=$CONFIG" "WORK_HOME=$RUN_HOME" "$target"
done

CURRENT_STAGE=signoff
signoff="$("$PROJECT_ROOT/scripts/check_signoff.sh" \
  "$STATUS_DIR/results/sky130hd/gcd/base" \
  "$STATUS_DIR/reports/sky130hd/gcd/base" \
  "$STATUS_DIR/logs/sky130hd/gcd/base")"
printf '%s\n' "$signoff"
timing="$(sed -n 's/^timing: \(.*\); not met$/\1/p' <<<"$signoff")"
if [[ -n "$timing" ]]; then
  echo "WARNING: GCD baseline timing not met ($timing);" \
    "baseline gates toolchain/DRC/LVS only" >&2
fi

touch "$STATUS_DIR/PASS"
echo "GCD baseline toolchain/DRC/LVS gate passed"
```

`scripts/check_signoff.sh` is the shared host-side verdict check used by both
run scripts; its behavior is covered by `tests/test_check_signoff.py` (clean
pass, DRC count 3, LVS mismatch, missing LVS log, negative WNS with and
without `--require-timing`, missing WNS line).

- [ ] **Step 4: Implement custom run, clean, and GUI modes**

ORFS already writes extracted parasitics to `6_final.spef`; the run script
requires that file to be non-empty instead of re-exporting it.

```bash
#!/usr/bin/env bash
# scripts/run_systolic2x2.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_HOME=/work/work/systolic2x2
CONFIG=/work/examples/systolic2x2/config.mk
STATUS_DIR="$PROJECT_ROOT/work/systolic2x2"

usage() {
  echo "usage: $0 [--clean | --gui]" >&2
  exit 2
}

[[ $# -le 1 ]] || usage
case "${1:-}" in
  "") ;;
  --clean)
    rm -f "$STATUS_DIR/PASS"
    exec "$PROJECT_ROOT/scripts/orfs_container.sh" make \
      "DESIGN_CONFIG=$CONFIG" "WORK_HOME=$RUN_HOME" clean_all
    ;;
  --gui)
    exec "$PROJECT_ROOT/scripts/orfs_container.sh" --gui make \
      "DESIGN_CONFIG=$CONFIG" "WORK_HOME=$RUN_HOME" gui_final
    ;;
  *) usage ;;
esac

[[ -f "$PROJECT_ROOT/work/gcd/PASS" ]] || {
  echo "run scripts/run_gcd_baseline.sh first" >&2
  exit 1
}

CURRENT_STAGE=preflight
trap 'echo "systolic2x2 failed during: $CURRENT_STAGE" >&2' ERR
rm -f "$STATUS_DIR/PASS"
mkdir -p "$STATUS_DIR"

for target in all drc lvs; do
  CURRENT_STAGE="$target"
  "$PROJECT_ROOT/scripts/orfs_container.sh" make \
    "DESIGN_CONFIG=$CONFIG" "WORK_HOME=$RUN_HOME" "$target"
done

RESULTS="$STATUS_DIR/results/sky130hd/systolic2x2/base"
REPORTS="$STATUS_DIR/reports/sky130hd/systolic2x2/base"
LOGS="$STATUS_DIR/logs/sky130hd/systolic2x2/base"
CURRENT_STAGE=verify_artifacts
test -s "$RESULTS/6_final.spef"
for artifact in 6_final.v 6_final.sdc 6_final.def 6_final.odb \
                6_final.cdl 6_lvs.lvsdb; do
  test -f "$RESULTS/$artifact"
done

CURRENT_STAGE=signoff
"$PROJECT_ROOT/scripts/check_signoff.sh" --require-timing \
  "$RESULTS" "$REPORTS" "$LOGS"

touch "$STATUS_DIR/PASS"
echo "systolic2x2 flow passed DRC, LVS, and timing checks (educational, not tapeout signoff)"
```

- [ ] **Step 5: Validate scripts without running the long flow**

Run:

```bash
chmod +x scripts/run_gcd_baseline.sh scripts/run_systolic2x2.sh \
  scripts/check_signoff.sh
bash -n scripts/run_gcd_baseline.sh scripts/run_systolic2x2.sh \
  scripts/check_signoff.sh
python3 -m unittest tests.test_project_contract tests.test_check_signoff -v
```

Expected: syntax checks and all contract tests pass.

- [ ] **Step 6: Run the baseline and custom implementation**

Run:

```bash
scripts/run_gcd_baseline.sh
scripts/run_systolic2x2.sh
```

Expected: both `work/gcd/PASS` and `work/systolic2x2/PASS` exist. If either
command fails, preserve its output and fix only the reported stage before
rerunning.

- [ ] **Step 7: Commit orchestration**

```bash
git add scripts/run_gcd_baseline.sh scripts/run_systolic2x2.sh \
  scripts/check_signoff.sh \
  tests/test_project_contract.py tests/test_check_signoff.py
git commit -m "feat: gate and run ORFS physical flows"
```

### Task 6: Honest metrics and signoff summary

**Files:**
- Create: `scripts/summarize_results.py`
- Create: `tests/test_summarize_results.py`
- Modify: `scripts/run_systolic2x2.sh`

**Interfaces:**
- Consumes: ORFS `metadata.json`, `6_drc_count.rpt`, `6_lvs.log`, final
  artifacts, and `work/toolchain-versions.txt`.
- Produces: `work/systolic2x2/summary.json` and `summary.md`.
- Classifies the run as `PASS`, `COMPLETED_WITH_FAILURES`, or `INCOMPLETE`.

- [ ] **Step 1: Write result-classification tests**

```python
# tests/test_summarize_results.py
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.summarize_results import summarize


class SummarizeResultsTest(unittest.TestCase):
    def make_run(self, root: Path, drc: str, lvs: str, with_gds=True):
        (root / "reports").mkdir(parents=True)
        (root / "logs").mkdir()
        (root / "results").mkdir()
        (root / "metadata.json").write_text(json.dumps({
            "synth__design__instance__count__stdcell": 128,
            "finish__design__instance__area": 456.5,
            "finish__design__core__utilization": 35.0,
            "finish__timing__setup__ws": 1.25,
            "finish__timing__setup__tns": 0.0,
            "finish__timing__clock__skew": 0.04,
            "finish__power__total": 0.003,
            "route__drc_errors": 0,
        }))
        (root / "reports/6_drc_count.rpt").write_text(drc)
        (root / "logs/6_lvs.log").write_text(lvs)
        if with_gds:
            (root / "results/6_final.gds").write_text("gds")

    def test_pass_requires_zero_drc_and_matching_lvs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root, "0\n", "Congratulations! Netlists match.\n")
            result = summarize(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["drc_count"], 0)
            self.assertEqual(result["lvs_status"], "PASS")

    def test_completed_failures_are_not_hidden(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root, "3\n", "Netlists do not match.\n")
            result = summarize(root)
            self.assertEqual(result["status"], "COMPLETED_WITH_FAILURES")
            self.assertEqual(result["lvs_status"], "FAIL")

    def test_missing_gds_is_incomplete(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root, "0\n", "Congratulations! Netlists match.\n",
                          with_gds=False)
            self.assertEqual(summarize(root)["status"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm the module is missing**

Run:

```bash
python3 -m unittest tests.test_summarize_results -v
```

Expected: import error for `scripts.summarize_results`.

- [ ] **Step 3: Implement the summary parser**

```python
#!/usr/bin/env python3
# scripts/summarize_results.py
import argparse
import json
import re
from pathlib import Path


METRICS = {
    "cell_count": "synth__design__instance__count__stdcell",
    "area_um2": "finish__design__instance__area",
    "utilization_pct": "finish__design__core__utilization",
    "wns_ns": "finish__timing__setup__ws",
    "tns_ns": "finish__timing__setup__tns",
    "clock_skew_ns": "finish__timing__clock__skew",
    "estimated_power_w": "finish__power__total",
    "route_drc_count": "route__drc_errors",
}


def summarize(run_dir: Path) -> dict:
    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}

    drc_path = run_dir / "reports/6_drc_count.rpt"
    drc_count = int(drc_path.read_text().strip()) if drc_path.exists() else None

    lvs_path = run_dir / "logs/6_lvs.log"
    lvs_text = lvs_path.read_text(errors="replace") if lvs_path.exists() else ""
    if re.search(r"Congratulations!\s+Netlists match", lvs_text, re.I):
        lvs_status = "PASS"
    elif re.search(r"do not match|mismatch|failed", lvs_text, re.I):
        lvs_status = "FAIL"
    else:
        lvs_status = "NOT_REPORTED"

    gds_exists = (run_dir / "results/6_final.gds").exists()
    if not gds_exists or drc_count is None or lvs_status == "NOT_REPORTED":
        status = "INCOMPLETE"
    elif drc_count == 0 and lvs_status == "PASS":
        status = "PASS"
    else:
        status = "COMPLETED_WITH_FAILURES"

    result = {
        "status": status,
        "drc_count": drc_count,
        "lvs_status": lvs_status,
        "power_note": "Vectorless ORFS estimate; not workload power.",
    }
    result.update({name: metadata.get(key, "NOT_REPORTED")
                   for name, key in METRICS.items()})
    return result


def write_outputs(run_dir: Path, result: dict) -> None:
    (run_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    lines = ["# systolic2x2 physical-design summary", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in result.items())
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.run_dir)
    write_outputs(args.run_dir, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run summary unit tests**

Run:

```bash
python3 -m unittest tests.test_summarize_results -v
```

Expected: all three tests pass.

- [ ] **Step 5: Generate ORFS metadata and summary after the custom flow**

Insert these commands immediately before `touch "$STATUS_DIR/PASS"` in
`scripts/run_systolic2x2.sh`:

```bash
"$PROJECT_ROOT/scripts/orfs_container.sh" python3 \
  /OpenROAD-flow-scripts/flow/util/genMetrics.py \
  --design systolic2x2 --platform sky130hd --flowVariant base \
  --logs /work/work/systolic2x2/logs/sky130hd/systolic2x2/base \
  --reports /work/work/systolic2x2/reports/sky130hd/systolic2x2/base \
  --results /work/work/systolic2x2/results/sky130hd/systolic2x2/base \
  --output /work/work/systolic2x2/metadata.json

cp "$STATUS_DIR/reports/sky130hd/systolic2x2/base/6_drc_count.rpt" \
  "$STATUS_DIR/reports/6_drc_count.rpt"
cp "$STATUS_DIR/logs/sky130hd/systolic2x2/base/6_lvs.log" \
  "$STATUS_DIR/logs/6_lvs.log"
ln -sfn results/sky130hd/systolic2x2/base "$STATUS_DIR/results-final"
mkdir -p "$STATUS_DIR/results"
ln -sfn ../results-final/6_final.gds "$STATUS_DIR/results/6_final.gds"

python3 "$PROJECT_ROOT/scripts/summarize_results.py" \
  --run-dir "$STATUS_DIR"
```

Replace the summary parser's GDS check with support for the canonical link:

```python
    gds_exists = (
        (run_dir / "results/6_final.gds").exists()
        or (run_dir / "results-final/6_final.gds").exists()
    )
```

- [ ] **Step 6: Regenerate the real summary and inspect status**

Run:

```bash
scripts/run_systolic2x2.sh
python3 -m json.tool work/systolic2x2/summary.json
```

Expected: summary files exist. `status` is `PASS` only if DRC is zero and LVS
matches; otherwise it truthfully reports `COMPLETED_WITH_FAILURES`.

- [ ] **Step 7: Commit reporting**

```bash
git add scripts/summarize_results.py scripts/run_systolic2x2.sh \
  tests/test_summarize_results.py
git commit -m "feat: summarize physical design and signoff"
```

### Task 7: User guide and reproducibility acceptance

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: all scripts and outputs from Tasks 1–6.
- Produces: exact setup/run/GUI/cleanup instructions and documented limits.

- [ ] **Step 1: Write the user guide**

```markdown
# OpenROAD AI-chip physical-design example

This project implements a four-PE, signed 8-bit 2×2 systolic array on the
SKY130HD platform. It demonstrates RTL synthesis through GDS,
KLayout DRC/LVS, OpenROAD GUI inspection, and basic PPA reporting.

## Run

```sh
scripts/check_environment.sh
scripts/run_gcd_baseline.sh
scripts/run_systolic2x2.sh
```

Open the final database:

```sh
scripts/run_systolic2x2.sh --gui
```

Clean only generated custom-flow stages:

```sh
scripts/run_systolic2x2.sh --clean
```

Results are under `work/systolic2x2/`. Read `summary.md` first, then inspect
the stage logs, reports, and final GDS/DEF/ODB files.

## Input protocol

Present two valid cycles for a 2×2 multiplication. Pack A row 0 in
`a_left[7:0]`, A row 1 in `a_left[15:8]`, B column 0 in `b_top[7:0]`, and B
column 1 in `b_top[15:8]`. Assert `start` on the first inner-dimension term
and `last` on the second. `done` pulses when all four accumulators are stable.

## Interpretation

The SKY130HD DRC/LVS result in this example is not a tapeout signoff. The
reported power is a default vectorless estimate and does not
represent an AI workload; VCD/SAIF-driven analysis is a later extension.
```

- [ ] **Step 2: Run all fast tests**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
scripts/orfs_container.sh yosys -q -s /work/tests/yosys/processing_element.ys
scripts/orfs_container.sh yosys -q -s /work/tests/yosys/systolic2x2.ys
bash -n scripts/*.sh
```

Expected: all Python and Yosys tests pass; every shell script parses.

- [ ] **Step 3: Perform a clean reproducibility run**

Run:

```bash
scripts/run_systolic2x2.sh --clean
rm -f work/systolic2x2/PASS \
  work/systolic2x2/summary.json work/systolic2x2/summary.md
scripts/run_systolic2x2.sh
test -f work/systolic2x2/results-final/6_final.gds
test -f work/systolic2x2/summary.json
```

Expected: the clean rerun reaches summary generation and reproduces all final
artifacts. A nonzero summary exit is acceptable only when
`summary.json.status` is `COMPLETED_WITH_FAILURES`; the underlying DRC/LVS
details must remain visible.

- [ ] **Step 4: Verify GUI launch separately**

Run from an X11 desktop session:

```bash
scripts/run_systolic2x2.sh --gui
```

Expected: OpenROAD GUI opens the final database. Closing the GUI returns to the
shell without altering batch results.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md
git commit -m "docs: explain OpenROAD systolic example"
```

- [ ] **Step 6: Final repository verification**

Run:

```bash
git status --short
git log --oneline --max-count=10
```

Expected: no tracked changes remain; nested tool checkouts and generated
`work/` files are ignored; the implementation commits are visible.

## Execution amendment (2026-10-19)

The explicit `scripts/export_spef.tcl` step was removed. ORFS already writes
extracted parasitics to `6_final.spef`; re-reading that file in a bare ODB
session failed because no Liberty libraries were loaded. `run_systolic2x2.sh`
now requires ORFS's `6_final.spef` to be non-empty before writing `PASS`.
Because ORFS `make drc` and the sky130hd LVS deck exit 0 even on violations,
both run scripts now call the shared host-side `scripts/check_signoff.sh`,
which requires a DRC count of exactly `0` and an LVS match verdict, and (for
`run_systolic2x2.sh` via `--require-timing`) a non-negative final WNS; the GCD
baseline only warns on its upstream negative WNS.
