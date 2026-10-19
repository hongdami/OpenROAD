#!/usr/bin/env bash
# scripts/run_gcd_baseline.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_HOME=/work/work/gcd
CONFIG=/OpenROAD-flow-scripts/flow/designs/nangate45/gcd/config.mk
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

test -f "$STATUS_DIR/results/nangate45/gcd/base/6_final.gds"
test -f "$STATUS_DIR/reports/nangate45/gcd/base/6_drc_count.rpt"
touch "$STATUS_DIR/PASS"
echo "GCD baseline passed"
