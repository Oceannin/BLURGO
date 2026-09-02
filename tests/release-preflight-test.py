"""Contract tests for BlurGo's release-preflight policy."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_preflight():
    script_path = Path(__file__).resolve().parents[1] / "tools" / "release-preflight.py"
    spec = importlib.util.spec_from_file_location("blurgo_release_preflight", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load release preflight from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = load_preflight()
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class RepositoryPolicyTests(unittest.TestCase):
    def test_current_repository_passes_standard_preflight(self) -> None:
        self.assertEqual(PREFLIGHT.standard_errors(REPOSITORY_ROOT), [])


class TagPolicyTests(unittest.TestCase):
    def create_signed_candidate(self, root: Path) -> None:
        (root / "buildspec.json").write_text(
            json.dumps({"version": "0.1.0"}), encoding="utf-8"
        )
        qa = root / "docs" / "qa"
        qa.mkdir(parents=True)
        (qa / "0.1.0-gate-status.md").write_text(
            "Decision: **ready to tag**\n\n"
            "- [x] Representative real-game capture.\n"
            "- [x] Forced GPU loss/reinitialization recovery.\n"
            "- [x] Maintainer manual QA sign-off.\n"
            "- [ ] Public `0.1.0` tag and GitHub Release.\n",
            encoding="utf-8",
        )
        fields = (
            "- Date: 2026-09-02",
            "- Tester: Test maintainer",
            "- BlurGo commit/package SHA-256: " + "a" * 64,
            "- OBS Studio version: 32.2.2",
            "- Operating system/build: Windows 11 24H2",
            "- GPU/driver: Test GPU / test driver",
            "- Graphics backend: Direct3D 11",
            "- Canvas/output/FPS and SDR/HDR format: 1920x1080/60 SDR",
            "- Game/title/version and capture mode: Authorized test title / Game Capture",
            "Baseline: 0.2 ms, 0 skipped",
            "Gaussian: 0.4 ms, 0 skipped",
            "Box: 0.4 ms, 0 skipped",
            "Pixelate: 0.3 ms, 0 skipped",
            "Lifecycle/alt-tab notes: passed",
            "OBS log path or private attachment: private-log.txt",
            "Harness report path or private attachment: private-report.json",
            "Trigger/method: approved disposable lab reset",
            "Recovery time: 3 seconds",
            "Observed fallback/recovery: recovered",
            "Restart persistence: passed",
            "OBS/crash log path or private attachment: private-gpu-log.txt",
            "Maintainer/name: Test maintainer",
            "Decision date: 2026-09-02",
            "Decision: `approve`",
        )
        manual = "\n".join(fields) + "\n- [x] All manual checks passed.\n"
        (qa / "0.1.0-manual-signoff.md").write_text(manual, encoding="utf-8")

    def test_complete_candidate_passes_tag_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_signed_candidate(root)
            self.assertEqual(PREFLIGHT.tag_errors(root, "0.1.0"), [])

    def test_incomplete_candidate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.create_signed_candidate(root)
            manual_path = root / "docs" / "qa" / "0.1.0-manual-signoff.md"
            manual = manual_path.read_text(encoding="utf-8")
            manual_path.write_text(
                manual.replace("Decision: `approve`", "Decision: `reject`").replace(
                    "- [x] All manual checks passed.", "- [ ] All manual checks passed."
                ),
                encoding="utf-8",
            )

            errors = PREFLIGHT.tag_errors(root, "0.1.0")

            self.assertTrue(any("unchecked item" in error for error in errors))
            self.assertTrue(any("not exactly `approve`" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
