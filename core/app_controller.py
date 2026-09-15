"""Ordered assessment pipeline and independent Guardian worker lifecycle."""

import multiprocessing as mp
from queue import Empty
from time import monotonic, perf_counter

from PySide6.QtCore import QObject, QTimer, Signal
from config.camera_config import CAMERA_INDEX, FRAME_STALE_SECONDS
from domain.operator_state import OperatorState, check_freshness
from modules.safedig_guardian.camera import capture_worker


class GuardianController(QObject):
    observation_ready = Signal(object, object)

    def __init__(self, parent=None, camera_index: int = CAMERA_INDEX) -> None:
        super().__init__(parent)
        self.camera_index = camera_index
        self._process = self._stop = self._queue = None
        self.state = OperatorState()
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self.stop()
        context = mp.get_context("spawn")
        self._stop = context.Event()
        self._queue = context.Queue(maxsize=1)
        self._process = context.Process(target=capture_worker,
                                        args=(self._stop, self._queue, self.camera_index), daemon=True)
        try:
            self._process.start()
        except (OSError, RuntimeError) as error:
            self.state = OperatorState(diagnostic=f"Camera worker unavailable: {error}")
            self._queue.close()
            self._process = self._queue = self._stop = None
            self.observation_ready.emit(self.state, None)
            return
        self.state = OperatorState(diagnostic="Opening camera")
        self.observation_ready.emit(self.state, None)
        self._timer.start()

    def _poll(self) -> None:
        packet = None
        try:
            # Bounded draining: stale queued frames never accumulate in the GUI.
            for _ in range(2):
                packet = self._queue.get_nowait()
        except Empty:
            pass
        if packet is not None:
            self.state, frame = packet
            self.state = check_freshness(self.state, monotonic(), FRAME_STALE_SECONDS)
            self.observation_ready.emit(self.state, frame if self.state.camera_available else None)
        fresh = check_freshness(self.state, monotonic(), FRAME_STALE_SECONDS)
        if fresh != self.state:
            self.state = fresh
            self.observation_ready.emit(self.state, None)
        if not self._process.is_alive():
            self._timer.stop()
            if self.state.camera_available:
                self.state = OperatorState(diagnostic="Camera worker stopped; retry camera")
                self.observation_ready.emit(self.state, None)

    def stop(self) -> None:
        self._timer.stop()
        if self._process is not None:
            self._stop.set()
            self._process.join(timeout=1.0)
            if self._process.is_alive():
                # Bound shutdown even when a native webcam driver blocks read().
                self._process.terminate()
                self._process.join(timeout=1.0)
            if self._process.is_alive():
                self._process.kill()
                self._process.join()
            self._process.close()
            self._queue.close()
            self._process = self._queue = self._stop = None


class AssessmentController:
    """One ordered assessment on the existing update cadence; no additional timer."""
    def __init__(self, risk_engine, decision_engine):
        from core.sensor_fusion import SensorFusion
        self.fusion = SensorFusion()
        self.risk = risk_engine
        self.decision = decision_engine

    def update(self, state, now=None):
        from dataclasses import replace
        started = perf_counter()
        state = replace(state, fusion=self.fusion.fuse(state, now))
        fused = perf_counter()
        state = self.risk.update(state)
        assessed = perf_counter()
        state = self.decision.update(state)
        decided = perf_counter()
        self.latencies = dict(fusion_latency_ms=(fused-started)*1000,
            risk_latency_ms=(assessed-fused)*1000, decision_latency_ms=(decided-assessed)*1000)
        return state


class ScenarioController:
    """Runs input adapters through existing modules, then the assessment pipeline."""
    def __init__(self, manager):
        self.manager = manager
        from services.data_recorder import DataRecorder
        self.recorder = DataRecorder()
        self.reset_engines()

    def reset_engines(self):
        from simulation.scenario_inputs import ScenarioInputs
        from modules.safedig_vision.utility_detector import UtilityDetector
        from modules.safedig_precision.design_conflict import DesignConflictEngine
        from core.safe_envelope import SafeEnvelopeEngine
        from core.risk_engine import RiskEngine
        from core.decision_engine import DecisionEngine
        self.inputs = ScenarioInputs()
        self.utility = UtilityDetector()
        self.envelope = SafeEnvelopeEngine()
        self.design = DesignConflictEngine()
        self.assessment = AssessmentController(RiskEngine(), DecisionEngine())

    def evaluate(self, timestamp=None, live_operator=None):
        timestamp = monotonic() if timestamp is None else timestamp
        state = self.inputs.sample(self.manager, timestamp, live_operator)
        state = self.utility.update(state, state.machine)
        state = self.envelope.update(state)
        state = self.design.update(state)
        state = self.assessment.update(state, timestamp)
        self.recorder.observe(state,self.manager.state.elapsed_time_s,self.assessment.latencies,self.inputs.guardian_source,self.inputs.faults.states)
        if self.manager.state.status == "COMPLETED":
            self.recorder.finalize("COMPLETED")
        return state
