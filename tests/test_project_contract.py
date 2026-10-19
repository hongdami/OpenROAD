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


if __name__ == "__main__":
    unittest.main()
