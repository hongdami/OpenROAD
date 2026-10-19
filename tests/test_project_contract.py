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

    def test_orfs_configuration_contract(self):
        config = (ROOT / "examples/systolic2x2/config.mk").read_text()
        sdc = (ROOT / "examples/systolic2x2/constraint.sdc").read_text()
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

    def test_orfs_signed_port_compatibility_adapter(self):
        config = (ROOT / "examples/systolic2x2/config.mk").read_text()
        canonicalize = (
            ROOT / "examples/systolic2x2/orfs_canonicalize.tcl"
        ).read_text()
        adapter = (
            ROOT / "examples/systolic2x2/orfs_unsigned_top.v"
        ).read_text()
        self.assertIn(
            "SYNTH_CANONICALIZE_TCL = "
            "/work/examples/systolic2x2/orfs_canonicalize.tcl",
            config,
        )
        self.assertIn(
            "rename systolic2x2 systolic2x2_signed", canonicalize
        )
        self.assertIn("module systolic2x2", adapter)
        self.assertIn("systolic2x2_signed wrapped_design", adapter)


if __name__ == "__main__":
    unittest.main()
