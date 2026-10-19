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

    def test_flow_scripts_preserve_stage_failures(self):
        baseline = (ROOT / "scripts/run_gcd_baseline.sh").read_text()
        custom = (ROOT / "scripts/run_systolic2x2.sh").read_text()
        self.assertIn("set -euo pipefail", baseline)
        self.assertIn("set -euo pipefail", custom)
        self.assertLess(baseline.index(" all"), baseline.index(" drc"))
        self.assertLess(baseline.index(" drc"), baseline.index(" lvs"))
        self.assertIn('[[ -f "$PROJECT_ROOT/work/gcd/PASS" ]]', custom)
        self.assertIn("gui_final", custom)

    def test_orfs_configuration_contract(self):
        config = (ROOT / "examples/systolic2x2/config.mk").read_text()
        sdc = (ROOT / "examples/systolic2x2/constraint.sdc").read_text()
        pdn = (ROOT / "examples/systolic2x2/pdn.tcl").read_text()
        for value in (
            "DESIGN_NAME = systolic2x2",
            "PLATFORM = nangate45",
            "/work/examples/systolic2x2/rtl/processing_element.sv",
            "/work/examples/systolic2x2/rtl/systolic2x2.sv",
            "CORE_UTILIZATION ?= 35",
        ):
            self.assertIn(value, config)
        self.assertIn("set clk_period 10.0", sdc)
        self.assertIn("create_clock", sdc)
        for value in (
            "set_voltage_domain -name CORE -power VDD -ground VSS",
            "define_pdn_grid -name grid -voltage_domains CORE -pins metal7",
            "add_pdn_stripe -grid grid -layer metal1",
            "add_pdn_stripe -grid grid -layer metal4",
            "add_pdn_stripe -grid grid -layer metal7",
            "add_pdn_connect -grid grid -layers {metal1 metal4}",
            "add_pdn_connect -grid grid -layers {metal4 metal7}",
        ):
            self.assertIn(value, pdn)

    def test_orfs_signed_port_compatibility_adapter(self):
        config = (ROOT / "examples/systolic2x2/config.mk").read_text()
        canonicalize = (
            ROOT / "examples/systolic2x2/orfs_canonicalize.tcl"
        ).read_text()
        adapter = (
            ROOT / "examples/systolic2x2/orfs_unsigned_top.v"
        ).read_text()
        adapter_test = (
            ROOT / "tests/yosys/orfs_adapter.ys"
        ).read_text()
        adapter_test_driver = (
            ROOT / "tests/yosys/orfs_adapter.tcl"
        ).read_text()
        self.assertIn(
            "SYNTH_CANONICALIZE_TCL = "
            "/work/examples/systolic2x2/orfs_canonicalize.tcl",
            config,
        )
        commands = [
            line.strip()
            for line in canonicalize.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            commands,
            [
                "yosys rename systolic2x2 systolic2x2_signed",
                "read_verilog "
                "/work/examples/systolic2x2/orfs_unsigned_top.v",
                "hierarchy -check -top systolic2x2",
            ],
        )
        adapter_code = "\n".join(
            line.split("//", 1)[0] for line in adapter.splitlines()
        )
        self.assertNotRegex(
            adapter_code,
            r"\b(?:input|output)\b[^,;)]*\bsigned\b",
        )
        for operator in (
            "$signed",
            "$unsigned",
            "{",
            "}",
            "+",
            "-",
            "*",
            "/",
            "%",
            "?",
            "&",
            "|",
            "^",
            "~",
            "!",
            "'",
        ):
            self.assertNotIn(operator, adapter_code)
        for value in (
            "tcl /work/tests/yosys/orfs_adapter.tcl",
            "select -assert-count 12 x:*",
            "select -assert-count 1 c:wrapped_design",
            "select -assert-count 1 c:*",
            "connect -assert -port wrapped_design a_left a_left",
            "connect -assert -port wrapped_design c11 c11",
        ):
            self.assertIn(value, adapter_test)
        for port in (
            "clk",
            "reset",
            "valid_in",
            "start",
            "last",
            "a_left",
            "b_top",
            "c00",
            "c01",
            "c10",
            "c11",
            "done",
        ):
            self.assertIn(
                f"connect -assert -port wrapped_design {port} {port}",
                adapter_test,
            )
        for port_contract in (
            "i:clk",
            "i:reset",
            "i:valid_in",
            "i:start",
            "i:last",
            "i:a_left s:16 %i",
            "i:b_top s:16 %i",
            "o:c00 s:24 %i",
            "o:c01 s:24 %i",
            "o:c10 s:24 %i",
            "o:c11 s:24 %i",
            "o:done",
        ):
            self.assertIn(
                f"select -assert-count 1 {port_contract}",
                adapter_test,
            )
        self.assertEqual(
            adapter_test_driver.splitlines(),
            [
                "yosys -import",
                "source "
                "/work/examples/systolic2x2/orfs_canonicalize.tcl",
            ],
        )


if __name__ == "__main__":
    unittest.main()
