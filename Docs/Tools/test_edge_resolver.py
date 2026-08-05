import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("edge_resolver.py")
SPEC = importlib.util.spec_from_file_location("edge_resolver", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuildCommandTests(unittest.TestCase):
    def test_build_preserves_existing_db_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            fixture_path = tmpdir_path / "fixture.yaml"
            fixture_path.write_text("fixture: value\n", encoding="utf-8")
            db_path = tmpdir_path / "components.db"
            db_path.write_text("keep me\n", encoding="utf-8")

            with patch.object(MODULE, "check_fixture", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    MODULE.build_database(fixture_path, db_path)

            self.assertEqual("keep me\n", db_path.read_text(encoding="utf-8"))

    def test_build_replaces_existing_db_only_after_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            fixture_path = tmpdir_path / "fixture.yaml"
            fixture_path.write_text("fixture: value\n", encoding="utf-8")
            db_path = tmpdir_path / "components.db"
            db_path.write_text("keep me\n", encoding="utf-8")

            def fake_check_fixture(received_fixture_path, received_obs_db, db_path=None):
                self.assertEqual(fixture_path, Path(received_fixture_path))
                self.assertTrue(received_obs_db.endswith("observations.db"))
                self.assertIsNotNone(db_path)
                Path(db_path).write_text("rebuilt\n", encoding="utf-8")
                return 0

            with patch.object(MODULE, "check_fixture", side_effect=fake_check_fixture):
                result = MODULE.build_database(fixture_path, db_path)

            self.assertEqual(0, result)
            self.assertEqual("rebuilt\n", db_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
