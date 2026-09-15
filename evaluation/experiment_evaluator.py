"""Single-run engineering KPIs; samples are not independent accuracy trials."""
from evaluation.metrics import average, minimum, maximum, absolute_error, depth_error, detection_outcome, true_distance

RISK_LEVELS = ["SAFE","CAUTION","HIGH","CRITICAL"]
ACTIONS = ["NORMAL","WARN","SLOW","VERIFY","RESTRICT"]

class ExperimentEvaluator:
    def __init__(self, truth):
        self.truth = truth
        self.history = []

    def observe(self, row):
        self.history.append(dict(row))

    def summarize(self, events, duration_s):
        rows = self.history
        values = lambda key: [r.get(key) for r in rows]
        def first(event, target=None):
            return next((e["simulation_time_s"] for e in events if e["event_type"] == event
                         and (target is None or e["data"].get("to") == target)), None)
        def highest(key, order):
            found = [v for v in values(key) if v in order]
            return max(found,key=order.index) if found else None
        eligible = [r for r in rows if r.get("detection_available")]
        detected = [r for r in eligible if r.get("utility_detected")]
        estimate = detected[-1] if detected else eligible[-1] if eligible else {}
        detected_any = bool(detected) if eligible else None
        truth = self.truth
        error = depth_error(estimate.get("estimated_utility_depth_m"),truth.utility_depth_m) if truth.utility_present and detected else depth_error(None,None)
        risk_time = {level:0. for level in RISK_LEVELS}
        fatigue_time = {"elevated":0.,"high":0.}
        # Left-hold integration in simulation time. Pause has zero simulation duration.
        for i,row in enumerate(rows):
            end = rows[i+1]["simulation_time_s"] if i+1<len(rows) else duration_s
            dt = max(0.,end-row["simulation_time_s"])
            if row.get("risk_level") in risk_time: risk_time[row["risk_level"]] += dt
            score = row.get("fatigue_score")
            if score is not None:
                if score >= 60: fatigue_time["high"] += dt
                elif score >= 30: fatigue_time["elevated"] += dt
        warning = next((r for r in rows if r.get("decision_action") in ("WARN","VERIFY","SLOW","RESTRICT")),None)
        true_distances = [true_distance(r.get("bucket_x_m"),r.get("bucket_z_m"),truth) for r in rows]
        proximity_errors = [absolute_error(r.get("distance_to_utility_m"),d) for r,d in zip(rows,true_distances)]
        max_depth = maximum(values("current_depth_m"))
        overdig = maximum([max(r["current_depth_m"]-r["target_depth_m"],0.) for r in rows
            if r.get("current_depth_m") is not None and r.get("target_depth_m") is not None])
        fatigue_available = any(v is not None for v in values("fatigue_score"))
        return dict(label="PROTOTYPE / SIMULATION EVALUATION", duration_s=duration_s,
            detection=dict(outcome=detection_outcome(truth.utility_present,detected_any),
                policy="At least one detection in available observations during this run; not frame-level accuracy",
                evaluated_samples=len(eligible), detected_samples=len(detected),
                utility_present=truth.utility_present, true_depth_m=truth.utility_depth_m if truth.utility_present else None,
                estimated_depth_m=estimate.get("estimated_utility_depth_m") if detected else None,
                predicted_confidence=estimate.get("utility_confidence") if detected else None,
                position_error_m=absolute_error(estimate.get("estimated_utility_x_m"),truth.utility_x_m) if truth.utility_present and detected else None,
                **error),
            proximity=dict(minimum_bucket_utility_distance_m=minimum(values("distance_to_utility_m")),
                minimum_true_bucket_utility_distance_m=minimum(true_distances),
                average_distance_error_m=average(proximity_errors),
                minimum_clearance_margin_m=minimum(values("clearance_margin_m")),
                warning_lead_distance_m=true_distance(warning.get("bucket_x_m"),warning.get("bucket_z_m"),truth) if warning else None),
            precision=dict(maximum_depth_m=max_depth, overdig_m=overdig,
                design_conflict_occurred="DESIGN_CONFLICT" in values("design_conflict"),
                first_design_conflict_time_s=first("DESIGN_CONFLICT_DETECTED"),
                minimum_planned_clearance_m=minimum(values("planned_clearance_m"))),
            guardian=dict(max_fatigue_score=maximum(values("fatigue_score")),average_fatigue_score=average(values("fatigue_score")),
                time_fatigue_elevated_s=fatigue_time["elevated"] if fatigue_available else None,
                time_fatigue_high_s=fatigue_time["high"] if fatigue_available else None),
            risk=dict(max_risk_score=maximum(values("risk_score")),average_risk_score=average(values("risk_score")),
                max_risk_level=highest("risk_level",RISK_LEVELS),
                **{"time_in_"+k.lower()+"_s":v for k,v in risk_time.items()},
                **{"time_to_"+k.lower()+"_s":first("RISK_LEVEL_CHANGED",k) for k in RISK_LEVELS[1:]}),
            decision=dict(final_decision=rows[-1].get("decision_action") if rows else None,
                highest_action=highest("decision_action",ACTIONS),
                time_to_first_warning_s=warning["simulation_time_s"] if warning else None,
                time_to_restrict_s=first("DECISION_CHANGED","RESTRICT"),
                **{"count_"+k.lower()+"_events":sum(e["event_type"]=="DECISION_CHANGED" and e["data"].get("to")==k for e in events) for k in ACTIONS[1:]}),
            latency=dict(label="PROTOTYPE SOFTWARE LATENCY",risk_engine_avg_ms=average(values("risk_latency_ms")),
                decision_engine_avg_ms=average(values("decision_latency_ms")),fusion_avg_ms=average(values("fusion_latency_ms"))))
