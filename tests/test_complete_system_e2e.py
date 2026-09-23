import importlib.util
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("complete_system", ROOT / "scripts/run_complete_system_e2e.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompleteSystemTests(unittest.TestCase):
    def test_source_audit_and_identifiability(self):
        data, audit = MODULE.load_and_audit(MODULE.DEFAULT_INPUT)
        self.assertEqual(len(data), 711)
        self.assertEqual(audit["repeat_units"], 1)
        self.assertEqual(audit["molecular_weights"], [80000.0])
        self.assertEqual(set(audit["identified_effects"]), {"salt", "molality", "temperature"})
        self.assertIn("repeat_unit", audit["non_identified_effects"])

    def test_candidate_grid_stays_inside_observed_support(self):
        data, _ = MODULE.load_and_audit(MODULE.DEFAULT_INPUT)
        candidates = MODULE.candidate_grid(data)
        for salt, group in candidates.groupby("salt_shortname"):
            observed = data[data["salt_shortname"] == salt]["molality"]
            self.assertGreaterEqual(group["molality"].min(), observed.min())
            self.assertLessEqual(group["molality"].max(), observed.max())
        self.assertTrue(candidates["temperature_K"].between(data["temperature_K"].min(), data["temperature_K"].max()).all())
        self.assertTrue(candidates["system_id"].is_unique)

    def test_polygen_candidates_are_quarantined_from_pcl_surrogate(self):
        audit = MODULE.polygen_interface_audit()
        self.assertEqual(len(audit), 25)
        self.assertFalse(audit["eligible_for_robust_ranking"].any())
        self.assertTrue(audit["surrogate_support"].eq("OOD_BLOCKED_repeat_unit_not_in_PCL_training").all())


if __name__ == "__main__":
    unittest.main()
