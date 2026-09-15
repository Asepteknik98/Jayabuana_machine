"""Deterministic software-only input faults. No assessment output writes."""
from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite
from random import Random
from adapters.sensor_source import SafeDigState, SensorHealth
from domain.operator_state import OperatorState, clear_guardian

class FaultType(str, Enum):
    NONE = "NONE"
    GPR_SIGNAL_DEGRADED = "GPR_SIGNAL_DEGRADED"
    GPR_OFFLINE = "GPR_OFFLINE"
    GPR_STALE = "GPR_STALE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    FALSE_POSITIVE_ANOMALY = "FALSE_POSITIVE_ANOMALY"
    FALSE_NEGATIVE_MISSED_UTILITY = "FALSE_NEGATIVE_MISSED_UTILITY"
    UTILITY_DEPTH_DRIFT = "UTILITY_DEPTH_DRIFT"
    UTILITY_POSITION_DRIFT = "UTILITY_POSITION_DRIFT"
    SIGNAL_NOISE_SPIKE = "SIGNAL_NOISE_SPIKE"
    GNSS_DEGRADED = "GNSS_DEGRADED"
    MACHINE_POSITION_STALE = "MACHINE_POSITION_STALE"
    GUARDIAN_OFFLINE = "GUARDIAN_OFFLINE"
    FACE_LOST = "FACE_LOST"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    FATIGUE_DATA_STALE = "FATIGUE_DATA_STALE"
    CONFLICTING_SENSOR_EVIDENCE = "CONFLICTING_SENSOR_EVIDENCE"

@dataclass(frozen=True)
class FaultState:
    fault_id: str
    fault_type: FaultType
    active: bool
    start_time_s: float
    duration_s: float
    severity: str
    source: str
    description: str
    recovered: bool
    timestamp: float


def validate_faults(faults, scenario_duration):
    if not isinstance(faults,list): raise ValueError("Faults must be a list")
    ids=set()
    for index,spec in enumerate(faults):
        if not isinstance(spec,dict): raise ValueError("Invalid fault")
        FaultType(spec["type"])
        key=str(spec.get("id",index))
        if key in ids: raise ValueError("Duplicate fault ID")
        ids.add(key)
        for name in ("start_time_s","duration_s"):
            v=spec[name]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) or v<0:
                raise ValueError("Invalid fault timing")
        if spec["duration_s"]<=0 or spec["start_time_s"]>scenario_duration: raise ValueError("Invalid fault interval")
        if spec.get("severity","MEDIUM") not in ("LOW","MEDIUM","HIGH"): raise ValueError("Invalid fault severity")
        if set(spec)-{"id","type","start_time_s","duration_s","severity","description","magnitude_m"}:
            raise ValueError("Only sensor fault parameters allowed")
        if "magnitude_m" in spec and (not isinstance(spec["magnitude_m"],(int,float)) or not isfinite(spec["magnitude_m"])):
            raise ValueError("Invalid drift magnitude")


class FaultInjectionEngine:
    def __init__(self):
        self.states=()
        self._frozen={}
        self.gnss=None

    def apply(self,state,specifications,elapsed,timestamp,seed=42,demo_mode=True,gnss=None):
        sensor,machine,operator=state.sensor,state.machine,state.operator
        self.gnss=gnss
        statuses=[]
        active_ids=set()
        for index,spec in enumerate(specifications):
            kind=FaultType(spec["type"])
            start,duration=spec["start_time_s"],spec["duration_s"]
            guardian=kind in (FaultType.GUARDIAN_OFFLINE,FaultType.FACE_LOST,FaultType.MULTIPLE_FACES,FaultType.FATIGUE_DATA_STALE)
            source="GUARDIAN" if guardian else "PRECISION" if kind in (FaultType.GNSS_DEGRADED,FaultType.MACHINE_POSITION_STALE) else "GPR"
            enabled=kind!=FaultType.NONE and (demo_mode or not guardian)
            active=enabled and start<=elapsed<start+duration
            key=str(spec.get("id",index))
            statuses.append(FaultState(key,kind,active,start,duration,spec.get("severity","MEDIUM"),source,
                spec.get("description",kind.value),enabled and elapsed>=start+duration,timestamp))
            if not active: continue
            active_ids.add(key)
            if kind==FaultType.GPR_OFFLINE:
                if sensor: sensor=replace(sensor,sensor_health=SensorHealth.OFFLINE)
            elif kind==FaultType.GPR_STALE and sensor:
                sensor=self._frozen.setdefault(key,replace(sensor,timestamp=timestamp-2.))
            elif kind in (FaultType.GPR_SIGNAL_DEGRADED,FaultType.LOW_CONFIDENCE) and sensor:
                sensor=replace(sensor,signal_quality=min(sensor.signal_quality,.35),confidence=.25,
                    sensor_health=SensorHealth.DEGRADED)
            elif kind==FaultType.FALSE_POSITIVE_ANOMALY and sensor:
                sensor=replace(sensor,anomaly_score=.9,anomaly_detected=True,confidence=.4,
                    sensor_health=SensorHealth.DEGRADED,response_profile="NARROW_CONDUIT")
            elif kind==FaultType.FALSE_NEGATIVE_MISSED_UTILITY and sensor:
                sensor=replace(sensor,signal_strength=.05,signal_quality=.25,confidence=.2,
                    anomaly_score=.05,anomaly_detected=False,estimated_x_m=None,estimated_z_m=None,
                    sensor_health=SensorHealth.DEGRADED)
            elif kind in (FaultType.UTILITY_DEPTH_DRIFT,FaultType.UTILITY_POSITION_DRIFT) and sensor:
                offset=spec.get("magnitude_m",.3)*min(1.,max(0.,(elapsed-start)/duration))
                if kind==FaultType.UTILITY_DEPTH_DRIFT and sensor.estimated_z_m is not None:
                    sensor=replace(sensor,estimated_z_m=sensor.estimated_z_m-offset)
                elif kind==FaultType.UTILITY_POSITION_DRIFT and sensor.estimated_x_m is not None:
                    sensor=replace(sensor,estimated_x_m=sensor.estimated_x_m+offset)
            elif kind==FaultType.SIGNAL_NOISE_SPIKE and sensor:
                # Seed and simulation tick make samples independent of rendering cadence.
                rng=Random(f"{seed}:{key}:{round(elapsed*10)}")
                sensor=replace(sensor,anomaly_score=.9+.1*rng.random(),anomaly_detected=True,
                    signal_strength=1.,confidence=.4,sensor_health=SensorHealth.DEGRADED)
            elif kind==FaultType.CONFLICTING_SENSOR_EVIDENCE and sensor:
                # Proxy disagreement: strong anomaly/confidence but poor propagation quality.
                sensor=replace(sensor,anomaly_score=.9,anomaly_detected=True,confidence=.95,
                    signal_quality=.25,sensor_health=SensorHealth.VALID)
            elif kind==FaultType.MACHINE_POSITION_STALE and machine:
                machine=self._frozen.setdefault(key,replace(machine,timestamp=timestamp-1.))
            elif kind==FaultType.GNSS_DEGRADED and machine:
                if gnss:self.gnss=replace(gnss,valid=False)
                machine=replace(machine,sensor_health=SensorHealth.DEGRADED)
            elif kind==FaultType.GUARDIAN_OFFLINE:
                operator=OperatorState(diagnostic="SIMULATED GUARDIAN OFFLINE")
            elif kind in (FaultType.FACE_LOST,FaultType.MULTIPLE_FACES) and operator:
                multiple=kind==FaultType.MULTIPLE_FACES
                operator=clear_guardian(replace(operator,face_count=2 if multiple else 0,face_detected=multiple,
                    valid=False,landmarks=(),landmarks_available=False,face_status="MULTIPLE FACES" if multiple else "NOT DETECTED",
                    analysis_status="AMBIGUOUS" if multiple else "UNAVAILABLE"))
            elif kind==FaultType.FATIGUE_DATA_STALE and operator:
                operator=self._frozen.setdefault(key,replace(operator,timestamp=timestamp-2.))
        self._frozen={k:v for k,v in self._frozen.items() if k in active_ids}
        self.states=tuple(statuses)
        derived=SafeDigState.from_sensor(sensor,timestamp)
        return replace(state,sensor=sensor,sensor_health=derived.sensor_health,status=derived.status,
            action_info=derived.action_info,machine=machine,operator=operator)
