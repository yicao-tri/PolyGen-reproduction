from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mingpt_split import build_split  # noqa: E402


DATA = ROOT / "vendor" / "PolyGen-1.0.0" / "minGPT" / "htp_md.csv"


class MinGPTSplitTest(unittest.TestCase):
    def test_released_split_leaks_every_positive_validation_row(self):
        result = build_split(DATA, "released-random", seed=42)
        positive = result.metadata["overlap_by_label"]["1"]
        self.assertEqual(positive["overlap_unique_structures"], 312)
        self.assertEqual(positive["validation_unique_structures"], 312)
        self.assertEqual(positive["overlap_validation_rows"], 1122)
        self.assertEqual(positive["validation_rows"], 1122)

    def test_corrected_split_is_disjoint_and_balances_training_only(self):
        result = build_split(DATA, "structure-disjoint", seed=42)
        metadata = result.metadata
        self.assertEqual(metadata["train"]["rows"], 9126)
        self.assertEqual(metadata["train"]["by_label"]["0"]["rows"], 4563)
        self.assertEqual(metadata["train"]["by_label"]["1"]["rows"], 4563)
        self.assertEqual(metadata["validation"]["by_label"]["0"]["rows"], 1141)
        self.assertEqual(metadata["validation"]["by_label"]["1"]["rows"], 64)
        self.assertTrue(
            all(
                values["overlap_unique_structures"] == 0
                for values in metadata["overlap_by_label"].values()
            )
        )

    def test_corrected_split_is_deterministic(self):
        first = build_split(DATA, "structure-disjoint", seed=42)
        second = build_split(DATA, "structure-disjoint", seed=42)
        self.assertTrue(first.train.equals(second.train))
        self.assertTrue(first.validation.equals(second.validation))


if __name__ == "__main__":
    unittest.main()
