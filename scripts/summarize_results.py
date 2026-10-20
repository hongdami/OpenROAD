#!/usr/bin/env python3
# scripts/summarize_results.py
# Summarizes an ORFS run into summary.json / summary.md. Status semantics
# mirror scripts/check_signoff.sh --require-timing.
import argparse
import json
import re
from pathlib import Path

NOT_REPORTED = "NOT_REPORTED"
LVS_MATCH = "Congratulations! Netlists match."
LVS_MISMATCH = "Netlists don't match"

METRICS = {
    "cell_count_synth": "synth__design__instance__count__stdcell",
    "cell_count_final": "finish__design__instance__count__stdcell",
    "area_um2": "finish__design__instance__area",
    "utilization_fraction": "finish__design__instance__utilization",
    "die_area_um2": "finish__design__die__area",
    "core_area_um2": "finish__design__core__area",
    "worst_setup_slack_ns": "finish__timing__setup__ws",
    "worst_hold_slack_ns": "finish__timing__hold__ws",
    "clock_skew_ns": "finish__clock__skew__setup",
    "setup_violation_count": "finish__timing__drv__setup_violation_count",
    "hold_violation_count": "finish__timing__drv__hold_violation_count",
    "estimated_power_w": "finish__power__total",
    "route_drc_count": "detailedroute__route__drc_errors",
}

NUMBER = r"-?\d+(?:\.\d+)?"


def read_text(path: Path) -> str | None:
    return path.read_text(errors="replace") if path.is_file() else None


def last_number(text: str, pattern: str):
    matches = re.findall(pattern, text, re.M)
    return float(matches[-1]) if matches else NOT_REPORTED


def parse_drc(path: Path) -> int | None:
    text = read_text(path)
    if text is None:
        return None
    text = "".join(text.split())
    return int(text) if re.fullmatch(r"[0-9]+", text) else None


def parse_lvs(path: Path) -> str:
    text = read_text(path) or ""
    if LVS_MISMATCH in text:
        return "FAIL"
    if LVS_MATCH in text:
        return "PASS"
    return NOT_REPORTED


def parse_finish(path: Path) -> dict:
    text = read_text(path) or ""
    clock = re.search(
        rf"^core_clock period_min = ({NUMBER}) fmax = ({NUMBER})", text, re.M)
    return {
        "wns_ns": last_number(text, rf"^wns max ({NUMBER})\s*$"),
        "tns_ns": last_number(text, rf"^tns max ({NUMBER})\s*$"),
        "period_min_ns": float(clock[1]) if clock else NOT_REPORTED,
        "fmax_mhz": float(clock[2]) if clock else NOT_REPORTED,
    }


def is_positive(value) -> bool:
    return isinstance(value, (int, float)) and value > 0


def load_metadata(path: Path) -> tuple[dict, bool]:
    text = read_text(path)
    if not text:
        return {}, False
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return {}, True
    if isinstance(loaded, dict):
        return loaded, False
    return {}, True


def summarize(results: Path, reports: Path, logs: Path, metadata: Path,
              toolchain: Path | None = None,
              run_command: str = NOT_REPORTED) -> dict:
    meta, malformed = load_metadata(metadata)
    gds = results / "6_final.gds"
    drc_count = parse_drc(reports / "6_drc_count.rpt")
    lvs_status = parse_lvs(logs / "6_lvs.log")
    timing = parse_finish(reports / "6_finish.rpt")
    toolchain_text = read_text(toolchain) if toolchain else None

    result = {name: meta.get(key, NOT_REPORTED)
              for name, key in METRICS.items()}
    result.update(timing)

    wns = timing["wns_ns"]
    counted = ("route_drc_count", "setup_violation_count", "hold_violation_count")
    metrics_missing = any(result[name] == NOT_REPORTED for name in counted)
    if (malformed or not (gds.is_file() and gds.stat().st_size > 0)
            or drc_count is None or lvs_status == NOT_REPORTED
            or wns == NOT_REPORTED or metrics_missing):
        status = "INCOMPLETE"
    elif (drc_count == 0 and lvs_status == "PASS" and wns >= 0
          and not any(is_positive(result[name]) for name in counted)):
        status = "PASS"
    else:
        status = "COMPLETED_WITH_FAILURES"

    result.update({
        "status": status,
        "drc_count": drc_count,
        "lvs_status": lvs_status,
        "toolchain": toolchain_text.strip() if toolchain_text else NOT_REPORTED,
        "power_note": "Vectorless ORFS estimate; not workload power.",
        "signoff_note":
            "SKY130HD DRC/LVS is an educational check, not tapeout signoff.",
        "run_command": run_command,
    })
    return result


def fmt(value, scale=1.0, digits=4) -> str:
    if value is None:
        return NOT_REPORTED
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value * scale:.{digits}g}"
    return str(value)


def render_markdown(r: dict) -> str:
    rows = [
        ("Status", r["status"]),
        ("Run command", r["run_command"]),
        ("DRC violations (KLayout)", fmt(r["drc_count"])),
        ("LVS", r["lvs_status"]),
        ("Setup WNS / TNS (ns)", f"{fmt(r['wns_ns'])} / {fmt(r['tns_ns'])}"),
        ("Worst setup / hold slack (ns)",
         f"{fmt(r['worst_setup_slack_ns'])} / {fmt(r['worst_hold_slack_ns'])}"),
        ("Setup / hold violations",
         f"{fmt(r['setup_violation_count'])} / "
         f"{fmt(r['hold_violation_count'])}"),
        ("Min period (ns) / fmax (MHz)",
         f"{fmt(r['period_min_ns'])} / {fmt(r['fmax_mhz'])}"),
        ("Clock skew (ns)", fmt(r["clock_skew_ns"])),
        ("Std cells (synth / final)",
         f"{fmt(r['cell_count_synth'])} / {fmt(r['cell_count_final'])}"),
        ("Cell area (um^2)", fmt(r["area_um2"], digits=6)),
        ("Core / die area (um^2)",
         f"{fmt(r['core_area_um2'], digits=6)} / "
         f"{fmt(r['die_area_um2'], digits=6)}"),
        ("Utilization (%)", fmt(r["utilization_fraction"], scale=100, digits=3)),
        ("Estimated power (mW)", fmt(r["estimated_power_w"], scale=1e3)),
        ("Detailed-route DRC errors", fmt(r["route_drc_count"])),
    ]
    lines = ["# systolic2x2 physical-design summary (SKY130HD)", "",
             "| Metric | Value |", "| --- | --- |"]
    lines += [f"| {name} | {value} |" for name, value in rows]
    lines += ["", "## Notes", "",
              f"- Power: {r['power_note']}",
              f"- Signoff: {r['signoff_note']}",
              "", "## Toolchain", "", "```", r["toolchain"], "```"]
    return "\n".join(lines) + "\n"


def write_outputs(out_dir: Path, result: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n")
    (out_dir / "summary.md").write_text(render_markdown(result))


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("results", "reports", "logs", "out-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--toolchain", type=Path)
    parser.add_argument("--run-command", required=True)
    args = parser.parse_args()
    result = summarize(args.results, args.reports, args.logs, args.metadata,
                       args.toolchain, args.run_command)
    write_outputs(args.out_dir, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
