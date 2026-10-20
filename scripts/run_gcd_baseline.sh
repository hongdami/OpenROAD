#!/usr/bin/env bash
# scripts/run_gcd_baseline.sh
# Toolchain sanity gate: flow + DRC + LVS. The upstream sky130hd GCD design
# misses timing at its own clock, so timing is reported but not required.
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
