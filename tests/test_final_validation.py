"""Startup contracts, fallback and final source-neutral regression checks."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
import unittest

from config.validation import validate_configuration
from config import risk_config,simulation_config,envelope_config,camera_config
from simulation.scenario_manager import ScenarioManager,SCENARIO_DIRECTORY
from core.app_controller import ScenarioController
from services.data_recorder import DataRecorder

class FinalValidationTests(unittest.TestCase):
    def test_configuration(self):
        self.assertEqual(validate_configuration(),[])
        for module,key,bad in ((risk_config,"WEIGHTS",{}),(risk_config,"WEIGHTS",None),
                (risk_config,"LEVEL_UP_THRESHOLDS",(60,30,80)),(risk_config,"LEVEL_UP_THRESHOLDS",None),
                (envelope_config,"BASE_SAFE_CLEARANCE_M",0),(simulation_config,"SIMULATION_DT",-1),
                (camera_config,"CAMERA_INDEX",-1)):
            with patch.object(module,key,bad):self.assertTrue(validate_configuration())

    def test_gpr_failure_and_recovery(self):
        manager=ScenarioManager();self.assertTrue(manager.load(SCENARIO_DIRECTORY/"critical_scenario.json"))
        controller=ScenarioController(manager)
        with patch.object(controller.inputs.gpr,"read",side_effect=RuntimeError("simulator failed")):
            with self.assertLogs("safedig",level="ERROR") as logs:
                state=controller.evaluate(100.)
                again=controller.evaluate(100.1)
            self.assertEqual(len(logs.records),1)
        self.assertEqual(state.sensor_health.value,"OFFLINE")
        self.assertEqual(again.decision.action.value,"VERIFY")
        for tick in range(3):state=controller.evaluate(101+tick*.1)
        self.assertEqual(state.decision.action.value,"NORMAL")

    def test_recorder_reset(self):
        manager=ScenarioManager();manager.load(SCENARIO_DIRECTORY/"critical_scenario.json")
        with TemporaryDirectory() as folder:
            recorder=DataRecorder(folder);recorder.start(manager.definition)
            exported=recorder.directory
            recorder.reset()
            self.assertIsNone(recorder.session)
            self.assertIsNone(recorder.summary)
            self.assertFalse(recorder.active)
            self.assertEqual(recorder.events.events,[])
            self.assertTrue((exported/"summary.json").is_file())

    def test_all_scenario_json(self):
        for path in SCENARIO_DIRECTORY.glob("*.json"):
            manager=ScenarioManager()
            self.assertTrue(manager.load(path),f"{path}: {manager.error}")

    def test_layer_import_boundaries(self):
        for folder in ("domain","evaluation","simulation"):
            for path in Path(folder).rglob("*.py"):
                tree=ast.parse(path.read_text(encoding="utf-8-sig"))
                for node in ast.walk(tree):
                    if isinstance(node,ast.ImportFrom):
                        self.assertFalse((node.module or "").startswith("ui"),str(path))
                        self.assertNotEqual(node.module,"PySide6.QtWidgets",str(path))
        for path in Path("core").glob("*.py"):
            self.assertNotIn("PySide6.QtWidgets",path.read_text(encoding="utf-8-sig"))
