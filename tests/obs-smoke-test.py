"""Dependency-free contract tests for the OBS runtime QA harness helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_harness():
    sys.modules.setdefault("websockets", types.ModuleType("websockets"))
    harness_path = Path(__file__).resolve().parents[1] / "tools" / "obs-smoke.py"
    spec = importlib.util.spec_from_file_location("blurgo_obs_smoke", harness_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load QA harness from {harness_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HARNESS = load_harness()


class CaptureSelectionTests(unittest.TestCase):
    def test_match_is_case_insensitive_across_name_and_value(self) -> None:
        items = [
            {"itemName": "Unrelated", "itemValue": "window:other", "itemEnabled": True},
            {
                "itemName": "Example GAME",
                "itemValue": "window:example.exe",
                "itemEnabled": True,
            },
        ]

        match = HARNESS.find_matching_property_item(items, "example game")

        self.assertIs(match, items[1])

    def test_disabled_and_empty_targets_are_ignored(self) -> None:
        items = [
            {"itemName": "Example Game", "itemValue": "disabled", "itemEnabled": False},
            {"itemName": "Example Game", "itemValue": "", "itemEnabled": True},
        ]

        self.assertIsNone(HARNESS.find_matching_property_item(items, "example"))


class RequiredCaptureTests(unittest.TestCase):
    def test_only_requested_non_passed_results_fail(self) -> None:
        failures = HARNESS.requested_capture_failures(
            {
                "display_capture": None,
                "window_capture": {"status": "passed"},
                "game_capture": {"status": "skipped", "reason": "hook unavailable"},
            }
        )

        self.assertEqual(failures, ["game_capture: hook unavailable"])

    def test_all_passed_results_are_accepted(self) -> None:
        failures = HARNESS.requested_capture_failures(
            {
                "window_capture": {"status": "passed"},
                "game_capture": {"status": "passed"},
            }
        )

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
