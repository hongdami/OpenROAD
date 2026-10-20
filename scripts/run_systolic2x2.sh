#!/usr/bin/env bash
# scripts/run_systolic2x2.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_HOME=/work/work/systolic2x2
CONFIG=/work/examples/systolic2x2/config.mk
STATUS_DIR="$PROJECT_ROOT/work/systolic2x2"

if [[ "${1:-}" == "--clean" ]]; then
  exec "$PROJECT_ROOT/scripts/orfs_container.sh" make \
    "DESIGN_CONFIG=$CONFIG" "WORK_HOME=$RUN_HOME" clean_all
fi

if [[ "${1:-}" == "--gui" ]]; then
  exec "$PROJECT_ROOT/scripts/orfs_container.sh" --gui make \
    "DESIGN_CONFIG=$CONFIG" "WORK_HOME=$RUN_HOME" gui_final
fi

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
CURRENT_STAGE=verify_artifacts
test -s "$RESULTS/6_final.spef"
for artifact in 6_final.v 6_final.sdc 6_final.def 6_final.odb \
                6_final.spef 6_final.gds 6_final.cdl 6_lvs.lvsdb; do
  test -f "$RESULTS/$artifact"
done
test -f "$REPORTS/6_drc_count.rpt"
touch "$STATUS_DIR/PASS"
echo "systolic2x2 flow completed; inspect timing, DRC, and LVS status"
