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

CURRENT_STAGE=metrics
"$PROJECT_ROOT/scripts/orfs_container.sh" python3 \
  /OpenROAD-flow-scripts/flow/util/genMetrics.py \
  --design systolic2x2 --platform sky130hd --flowVariant base \
  --logs "${LOGS/#"$STATUS_DIR"/$RUN_HOME}" \
  --reports "${REPORTS/#"$STATUS_DIR"/$RUN_HOME}" \
  --results "${RESULTS/#"$STATUS_DIR"/$RUN_HOME}" \
  --output "$RUN_HOME/metadata.json"

CURRENT_STAGE=summary
python3 "$PROJECT_ROOT/scripts/summarize_results.py" \
  --results "$RESULTS" --reports "$REPORTS" --logs "$LOGS" \
  --metadata "$STATUS_DIR/metadata.json" \
  --toolchain "$PROJECT_ROOT/work/toolchain-versions.txt" \
  --run-command "scripts/run_systolic2x2.sh" \
  --out-dir "$STATUS_DIR"

touch "$STATUS_DIR/PASS"
echo "systolic2x2 flow passed DRC, LVS, and timing checks (educational, not tapeout signoff)"
