from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_signoff.sh"

LVS_MATCH = (
    "INFO : Comparing netlists\n"
    "INFO : Congratulations! Netlists match.\n"
)
LVS_MISMATCH = (
    "INFO : Comparing netlists\n"
    "ERROR : Netlists don't match\n"
)


def finish_report(wns="0.00", tns="0.00"):
    lines = ["", "=" * 20, "report_tns", "-" * 20]
    if tns is not None:
        lines.append(f"tns max {tns}")
    lines += ["", "=" * 20, "report_wns", "-" * 20]
    if wns is not None:
        lines.append(f"wns max {wns}")
    return "\n".join(lines) + "\n"


class CheckSignoffTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.results = base / "results"
        self.reports = base / "reports"
        self.logs = base / "logs"
        for path in (self.results, self.reports, self.logs):
            path.mkdir()
        (self.results / "6_final.gds").write_bytes(b"GDS")
        (self.reports / "6_drc_count.rpt").write_text("0\n")
        (self.logs / "6_lvs.log").write_text(LVS_MATCH)
        (self.reports / "6_finish.rpt").write_text(finish_report())

    def tearDown(self):
        self._tmp.cleanup()

    def run_checker(self, *flags):
        return subprocess.run(
            [
                "bash",
                str(CHECKER),
                *flags,
                str(self.results),
                str(self.reports),
                str(self.logs),
            ],
            capture_output=True,
            text=True,
        )

    def assertFails(self, proc, reason):
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(reason, proc.stderr)

    def test_clean_signoff_passes_with_timing_required(self):
        proc = self.run_checker("--require-timing")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("wns max 0.00", proc.stdout)
        self.assertIn("tns max 0.00", proc.stdout)

    def test_drc_violations_fail(self):
        (self.reports / "6_drc_count.rpt").write_text("3\n")
        self.assertFails(self.run_checker(), "DRC")

    def test_missing_drc_count_fails(self):
        (self.reports / "6_drc_count.rpt").unlink()
        self.assertFails(self.run_checker(), "6_drc_count.rpt")

    def test_non_integer_drc_count_fails(self):
        (self.reports / "6_drc_count.rpt").write_text("0 0\n")
        self.assertFails(self.run_checker(), "DRC")

    def test_lvs_mismatch_fails(self):
        (self.logs / "6_lvs.log").write_text(LVS_MISMATCH)
        self.assertFails(self.run_checker(), "LVS")

    def test_lvs_mismatch_fails_even_with_match_line(self):
        (self.logs / "6_lvs.log").write_text(LVS_MATCH + LVS_MISMATCH)
        self.assertFails(self.run_checker(), "LVS")

    def test_missing_lvs_log_fails(self):
        (self.logs / "6_lvs.log").unlink()
        self.assertFails(self.run_checker(), "6_lvs.log")

    def test_missing_gds_fails(self):
        (self.results / "6_final.gds").unlink()
        self.assertFails(self.run_checker(), "6_final.gds")

    def test_negative_wns_fails_only_when_timing_required(self):
        (self.reports / "6_finish.rpt").write_text(
            finish_report(wns="-1.40", tns="-62.69")
        )
        self.assertFails(self.run_checker("--require-timing"), "-1.40")
        proc = self.run_checker()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("wns max -1.40, tns max -62.69; not met", proc.stdout)

    def test_missing_wns_fails_when_timing_required(self):
        (self.reports / "6_finish.rpt").write_text(finish_report(wns=None))
        self.assertFails(self.run_checker("--require-timing"), "wns max")

    def test_unknown_option_is_rejected(self):
        proc = self.run_checker("--bogus")
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
