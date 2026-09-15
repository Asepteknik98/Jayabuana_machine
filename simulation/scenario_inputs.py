"""Simulation adapters. Ground truth stays upstream of the existing detector."""
from dataclasses import replace
import logging
from adapters.sensor_source import SafeDigState, SensorHealth
from domain.operator_state import OperatorState
from modules.safedig_vision.gpr_simulator import GPRSimulator
from simulation.excavator_simulator import ExcavatorSimulator
from simulation.machine_sensor_simulator import machine_state
from simulation.gnss_simulator import GNSSSimulator

class ScenarioInputs:
    vision_source = "SIMULATED_GPR"
    machine_source = "SIMULATED_MACHINE"

    def __init__(self):
        self.gpr = GPRSimulator()
        self._gpr_error = ""
        self.excavator = ExcavatorSimulator()
        self.gnss = GNSSSimulator()
        from simulation.fault_injection import FaultInjectionEngine
        self.faults = FaultInjectionEngine()

    def sample(self, manager, timestamp, live_operator=None):
        data, values = manager.definition, manager.inputs()
        self.gpr.set_soil(data["soil"]["type"])
        truth = data["utility_ground_truth"]
        try:
            sensor = self.gpr.read(timestamp, exposure=values["exposure"] if truth["enabled"] else 0.,
                utility_x_m=truth["x_m"], utility_depth_m=truth["depth_m"], simulation_time=manager.state.elapsed_time_s)
            if self._gpr_error:logging.getLogger("safedig").info("GPR simulator recovered")
            self._gpr_error = ""
        except (OSError, ValueError, RuntimeError, ArithmeticError) as error:
            if str(error) != self._gpr_error:
                logging.getLogger("safedig").error("GPR SIMULATOR UNAVAILABLE: %s",error)
            self._gpr_error = str(error)
            sensor = None
        position, geometry = self.excavator.sample(values, data["excavation"], manager.state.elapsed_time_s)
        machine = machine_state(position, geometry, values["plan_center_x_m"], timestamp)
        operator = live_operator
        if manager.state.demo_mode:
            fatigue = values["fatigue"]
            operator = OperatorState(camera_available=True, camera_health=SensorHealth.VALID,
                face_detected=True, face_count=1, valid=True, last_frame_timestamp=timestamp,
                last_detection_timestamp=timestamp, timestamp=timestamp, fatigue_valid=True,
                fatigue_score=fatigue, fatigue_level="HIGH" if fatigue >= 60 else "ELEVATED" if fatigue >= 30 else "NORMAL",
                fatigue_confidence=.9, attention_score=values["attention"],
                attention_status="DISTRACTED" if values["attention"] < .4 else "ATTENTIVE",
                analysis_status="SIMULATED GUARDIAN INPUT", diagnostic="SIMULATED DEMO; no camera image")
        self.guardian_source = "SIMULATED" if manager.state.demo_mode else "LIVE" if operator and operator.camera_available else "OFFLINE"
        self.position, self.geometry = position, geometry
        self.machine_origin = self.gnss.read(timestamp)
        state = replace(SafeDigState.from_sensor(sensor, timestamp), machine=machine, operator=operator)
        state = self.faults.apply(state,data.get("faults",[]),manager.state.elapsed_time_s,timestamp,
            data.get("seed",42),manager.state.demo_mode,self.machine_origin)
        self.machine_origin = self.faults.gnss
        if state.machine is not machine:
            from modules.safedig_precision.bucket_position import BucketPosition
            self.position = BucketPosition(state.machine.bucket_x_m,-state.machine.bucket_z_m)
            self.geometry = replace(geometry,current_depth_m=state.machine.current_depth_m,
                remaining_depth_m=state.machine.target_depth_m-state.machine.current_depth_m,
                bucket_speed_m_s=state.machine.bucket_speed_mps)
        return state
