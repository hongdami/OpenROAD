#!/usr/bin/env bash
# scripts/check_signoff.sh
# Host-side verdict check for an ORFS run. ORFS `make drc` and the sky130hd
# LVS deck both exit 0 on violations, so their reports must be inspected.
# SKY130HD DRC/LVS here is an educational check, not tapeout signoff.
set -euo pipefail

usage() {
  echo "usage: $0 [--require-timing] RESULTS_DIR REPORTS_DIR LOGS_DIR" >&2
  exit 2
}

fail() {
  echo "signoff FAILED: $*" >&2
  exit 1
}

REQUIRE_TIMING=0
if [[ "${1:-}" == "--require-timing" ]]; then
  REQUIRE_TIMING=1
  shift
fi
[[ $# -eq 3 ]] || usage
[[ "$1" != -* ]] || usage

RESULTS="$1"
REPORTS="$2"
LOGS="$3"

GDS="$RESULTS/6_final.gds"
DRC_COUNT="$REPORTS/6_drc_count.rpt"
LVS_LOG="$LOGS/6_lvs.log"
FINISH_RPT="$REPORTS/6_finish.rpt"

[[ -s "$GDS" ]] || fail "missing or empty $GDS"

[[ -f "$DRC_COUNT" ]] || fail "DRC count report missing: $DRC_COUNT"
drc="$(tr -d '[:space:]' <"$DRC_COUNT")"
[[ "$drc" =~ ^[0-9]+$ ]] ||
  fail "DRC count unparseable in $DRC_COUNT: '$(head -c 80 "$DRC_COUNT")'"
[[ "$drc" == 0 ]] || fail "DRC reported $drc violations ($DRC_COUNT)"
echo "DRC: 0 violations"

[[ -f "$LVS_LOG" ]] || fail "LVS log missing: $LVS_LOG"
if grep -qF "Netlists don't match" "$LVS_LOG"; then
  fail "LVS netlists don't match ($LVS_LOG)"
fi
grep -qF "Congratulations! Netlists match." "$LVS_LOG" ||
  fail "LVS log has no 'Netlists match' verdict ($LVS_LOG)"
echo "LVS: netlists match"

NUMBER='^-?[0-9]+(\.[0-9]+)?$'
wns=""
tns=""
if [[ -f "$FINISH_RPT" ]]; then
  wns="$(awk '$1 == "wns" && $2 == "max" { v = $3 } END { print v }' \
    "$FINISH_RPT")"
  tns="$(awk '$1 == "tns" && $2 == "max" { v = $3 } END { print v }' \
    "$FINISH_RPT")"
fi

if [[ ! "$wns" =~ $NUMBER ]]; then
  if [[ "$REQUIRE_TIMING" == 1 ]]; then
    fail "no numeric 'wns max' line in $FINISH_RPT"
  fi
  echo "WARNING: no numeric 'wns max' line in $FINISH_RPT" >&2
  echo "timing: wns max unknown, tns max ${tns:-unknown}; unknown"
  exit 0
fi

summary="wns max $wns, tns max ${tns:-unknown}"
if awk -v w="$wns" 'BEGIN { exit !(w + 0 < 0) }'; then
  if [[ "$REQUIRE_TIMING" == 1 ]]; then
    fail "timing not met ($summary)"
  fi
  echo "timing: $summary; not met"
else
  echo "timing: $summary; met"
fi
