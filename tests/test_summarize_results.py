import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.summarize_results import summarize  # noqa: E402

LVS_MATCH = "INFO : Comparing netlists\nINFO : Congratulations! Netlists match.\n"
LVS_MISMATCH = "INFO : Comparing netlists\nERROR : Netlists don't match\n"

METADATA = {
    "synth__design__instance__count__stdcell": 5276,
    "finish__design__instance__count__stdcell": 6300,
    "finish__design__instance__area": 28964.0,
    "finish__design__instance__utilization": 0.387755,
    "finish__design__die__area": 76867.6,
    "finish__design__core__area": 74696.6,
    "finish__timing__setup__ws": 3.69612,
    "finish__timing__hold__ws": 0.418518,
    "finish__clock__skew__setup": 0.0237157,
    "finish__timing__drv__setup_violation_count": 0,
    "finish__timing__drv__hold_violation_count": 0,
    "finish__power__total": 0.00368841,
    "detailedroute__route__drc_errors": 0,
}


def finish_report(wns="0.00", tns="0.00"):
    lines = ["report_tns", f"tns max {tns}", "report_wns"]
    if wns is not None:
        lines.append(f"wns max {wns}")
    lines += [
        "core_clock period_min = 4.86 fmax = 205.78",
        "vclk_core_clock period_min = 0.00 fmax = inf",
    ]
    return "\n".join(lines) + "\n"


class SummarizeResultsTest(unittest.TestCase):
    def make_run(self, root: Path, drc="0\n", lvs=LVS_MATCH, with_gds=True,
                 wns="0.00", metadata=None):
        dirs = {name: root / name for name in ("results", "reports", "logs")}
        for path in dirs.values():
            path.mkdir(parents=True)
        meta = dict(METADATA, **(metadata or {}))
        (root / "metadata.json").write_text(json.dumps(meta))
        (dirs["reports"] / "6_drc_count.rpt").write_text(drc)
        (dirs["reports"] / "6_finish.rpt").write_text(finish_report(wns))
        (dirs["logs"] / "6_lvs.log").write_text(lvs)
        if with_gds:
            (dirs["results"] / "6_final.gds").write_text("gds")
        return dict(results=dirs["results"], reports=dirs["reports"],
                    logs=dirs["logs"], metadata=root / "metadata.json")

    def test_pass_requires_zero_drc_matching_lvs_and_met_timing(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp)))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["drc_count"], 0)
        self.assertEqual(result["lvs_status"], "PASS")
        self.assertEqual(result["wns_ns"], 0.0)
        self.assertEqual(result["worst_setup_slack_ns"], 3.69612)
        self.assertEqual(result["estimated_power_w"], 0.00368841)
        self.assertEqual(result["cell_count_synth"], 5276)
        self.assertEqual(result["route_drc_count"], 0)
        self.assertEqual(result["period_min_ns"], 4.86)
        self.assertEqual(result["fmax_mhz"], 205.78)
        self.assertEqual(result["power_note"],
                         "Vectorless ORFS estimate; not workload power.")
        self.assertEqual(
            result["signoff_note"],
            "SKY130HD DRC/LVS is an educational check, not tapeout signoff.")
        self.assertEqual(result["toolchain"], "NOT_REPORTED")

    def test_completed_failures_are_not_hidden(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), drc="3\n",
                                               lvs=LVS_MISMATCH))
        self.assertEqual(result["status"], "COMPLETED_WITH_FAILURES")
        self.assertEqual(result["drc_count"], 3)
        self.assertEqual(result["lvs_status"], "FAIL")

    def test_benign_log_text_does_not_fail_lvs(self):
        log = "INFO : 0 devices failed to mismatch\n" + LVS_MATCH
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), lvs=log))
        self.assertEqual(result["lvs_status"], "PASS")

    def test_lvs_without_verdict_is_incomplete(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp),
                                               lvs="INFO : Comparing\n"))
        self.assertEqual(result["lvs_status"], "NOT_REPORTED")
        self.assertEqual(result["status"], "INCOMPLETE")

    def test_missing_gds_is_incomplete(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), with_gds=False))
        self.assertEqual(result["status"], "INCOMPLETE")

    def test_non_integer_drc_is_incomplete(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), drc="error\n"))
        self.assertIsNone(result["drc_count"])
        self.assertEqual(result["status"], "INCOMPLETE")

    def test_negative_wns_is_failure(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), wns="-0.12"))
        self.assertEqual(result["wns_ns"], -0.12)
        self.assertEqual(result["status"], "COMPLETED_WITH_FAILURES")

    def test_hold_violations_are_failure(self):
        meta = {"finish__timing__drv__hold_violation_count": 2}
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), metadata=meta))
        self.assertEqual(result["hold_violation_count"], 2)
        self.assertEqual(result["status"], "COMPLETED_WITH_FAILURES")

    def test_missing_wns_is_incomplete(self):
        with TemporaryDirectory() as tmp:
            result = summarize(**self.make_run(Path(tmp), wns=None))
        self.assertEqual(result["wns_ns"], "NOT_REPORTED")
        self.assertEqual(result["status"], "INCOMPLETE")

    def test_missing_metrics_are_not_reported(self):
        with TemporaryDirectory() as tmp:
            run = self.make_run(Path(tmp))
            run["metadata"].write_text("{}")
            result = summarize(**run)
        self.assertEqual(result["estimated_power_w"], "NOT_REPORTED")
        self.assertEqual(result["status"], "PASS")

    def test_cli_writes_outputs_and_reports_toolchain(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self.make_run(root)
            toolchain = root / "toolchain-versions.txt"
            toolchain.write_text("KLayout 0.30.12\n")
            out = root / "out"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts/summarize_results.py"),
                 "--results", run["results"], "--reports", run["reports"],
                 "--logs", run["logs"], "--metadata", run["metadata"],
                 "--toolchain", toolchain, "--out-dir", out],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = json.loads((out / "summary.json").read_text())
            md = (out / "summary.md").read_text()
        self.assertEqual(summary["toolchain"], "KLayout 0.30.12")
        self.assertIn("| Status | PASS |", md)
        self.assertIn("not workload power", md)
        self.assertIn("not tapeout signoff", md)

    def test_cli_exits_nonzero_unless_pass(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self.make_run(root, drc="1\n")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts/summarize_results.py"),
                 "--results", run["results"], "--reports", run["reports"],
                 "--logs", run["logs"], "--metadata", run["metadata"],
                 "--out-dir", root / "out"],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertTrue((root / "out/summary.json").exists())


if __name__ == "__main__":
    unittest.main()
