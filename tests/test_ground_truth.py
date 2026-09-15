from dataclasses import replace
from pathlib import Path
import json
import unittest
from evaluation.ground_truth import GroundTruth
from simulation.scenario_manager import SCENARIO_DIRECTORY

class GroundTruthTests(unittest.TestCase):
    def test_scenario_truth(self):
        scenario=json.loads((SCENARIO_DIRECTORY/"critical_scenario.json").read_text())
        truth=GroundTruth.from_scenario(scenario,100.)
        self.assertTrue(truth.utility_present)
        self.assertEqual(truth.utility_depth_m,1.32)
        self.assertEqual(truth.scenario_id,"critical_scenario")
        self.assertEqual(truth.timestamp,100.)
        scenario["utility_ground_truth"]["depth_m"]=8.
        self.assertEqual(truth.utility_depth_m,1.32)

    def test_no_truth_dependency_in_engines(self):
        for path in ("modules/safedig_vision/utility_detector.py","core/risk_engine.py","core/decision_engine.py"):
            source=Path(path).read_text(encoding="utf8")
            self.assertNotIn("evaluation.ground_truth",source)
            self.assertNotIn("utility_ground_truth",source)
