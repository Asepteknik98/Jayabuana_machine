"""Evaluation-only reliability checks. Never feed these results to assessment."""
from evaluation.metrics import average, maximum, absolute_error


def classification_metrics(tp,fp,fn,tn):
    ratio=lambda n,d:n/d if d else None
    return dict(precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),specificity=ratio(tn,tn+fp),
        false_positive_rate=ratio(fp,fp+tn),false_negative_rate=ratio(fn,fn+tp),accuracy=ratio(tp+tn,tp+fp+fn+tn))


def aggregate_experiments(summaries):
    # One outcome per unique completed experiment, never one sample per frame.
    runs={s["experiment_id"]:s for s in summaries if s.get("status")=="COMPLETED" and s.get("experiment_id")}
    outcomes=[s.get("detection",{}).get("outcome") for s in runs.values()]
    known=[v for v in outcomes if v in ("TRUE_POSITIVE","FALSE_POSITIVE","FALSE_NEGATIVE","TRUE_NEGATIVE")]
    if len(known)<2:return None
    return dict(experiment_count=len(known),**classification_metrics(*(known.count(k) for k in
        ("TRUE_POSITIVE","FALSE_POSITIVE","FALSE_NEGATIVE","TRUE_NEGATIVE"))))


def reliability_summary(truth,rows,events,outcome):
    count=lambda kind:sum(e["event_type"]==kind for e in events)
    starts=[e for e in events if e["event_type"]=="FAULT_STARTED"]
    details=[]
    for event in starts:
        fault_id=event["data"]["fault_id"]
        start=event["simulation_time_s"]
        matching=lambda kind:next((e["simulation_time_s"] for e in events if e["event_type"]==kind
            and e["data"].get("fault_id")==fault_id and e["simulation_time_s"]>=start),None)
        cleared,recovered=matching("FAULT_CLEARED"),matching("SENSOR_RECOVERED")
        domain=event["data"].get("source","GPR")
        relevant=[r for r in rows if r["simulation_time_s"]>=start
            and (cleared is None or r["simulation_time_s"]<=cleared)]
        degraded=next((r["simulation_time_s"] for r in relevant if
            not r.get({"GPR":"vision_valid","PRECISION":"precision_valid","GUARDIAN":"guardian_valid"}[domain],False)
            or (domain=="GPR" and r.get("sensor_health")!="VALID")
            or (domain=="PRECISION" and r.get("machine_health")!="VALID")
            or (domain=="GPR" and r.get("fusion_confidence")=="LOW")),None)
        verify=next((r["simulation_time_s"] for r in relevant if r.get("decision_action")=="VERIFY"),None)
        details.append(dict(fault_id=fault_id,fault_type=event["data"].get("fault_type"),fault_start_time=start,
            system_degraded_time=degraded,verification_decision_time=verify,sensor_recovery_time=recovered,
            fault_cleared_time=cleared,time_to_verification_s=verify-start if verify is not None else None,
            fault_response_latency_s=degraded-start if degraded is not None else None,
            time_to_recover_valid_state_s=recovered-cleared if recovered is not None and cleared is not None else None))
    false_safe=any(truth.utility_present and not r.get("utility_detected") and
        r.get("risk_level")=="SAFE" and r.get("decision_action")=="NORMAL" for r in rows)
    false_restrict=any(not truth.utility_present and r.get("utility_detected") and
        r.get("decision_action")=="RESTRICT" for r in rows)
    estimates=[r for r in rows if r.get("detection_available") and r.get("utility_detected") and truth.utility_present]
    depth_errors=[absolute_error(r.get("estimated_utility_depth_m"),truth.utility_depth_m) for r in estimates]
    position_errors=[absolute_error(r.get("estimated_utility_x_m"),truth.utility_x_m) for r in estimates]
    changes=[abs(b["risk_score"]-a["risk_score"]) for a,b in zip(rows,rows[1:])
             if a.get("risk_score") is not None and b.get("risk_score") is not None]
    return dict(label="SOFTWARE FAULT INJECTION / PROTOTYPE RELIABILITY",fault_count=len(starts),
        fault_recovery_count=count("SENSOR_RECOVERED"),
        mean_recovery_time_s=average([d["time_to_recover_valid_state_s"] for d in details]),
        false_positive_count=int(outcome=="FALSE_POSITIVE"),false_negative_count=int(outcome=="FALSE_NEGATIVE"),
        true_positive_count=int(outcome=="TRUE_POSITIVE"),true_negative_count=int(outcome=="TRUE_NEGATIVE"),
        verification_request_count=count("VERIFICATION_REQUIRED"),sensor_offline_count=count("SENSOR_OFFLINE"),
        sensor_stale_count=count("SENSOR_STALE"),sensor_degraded_count=count("SENSOR_DEGRADED"),
        risk_invalid_count=count("RISK_INVALID"),decision_fallback_count=count("DECISION_FALLBACK"),
        count_policy="Transitions/episodes; classification is one outcome per experiment",
        risk_level_transition_count=sum(e["event_type"]=="RISK_LEVEL_CHANGED" and e["data"].get("from") is not None for e in events),
        decision_transition_count=sum(e["event_type"]=="DECISION_CHANGED" and e["data"].get("from") is not None for e in events),
        max_transient_risk_change=maximum(changes),false_safe_condition=false_safe,
        false_restrict_condition=false_restrict,
        warning="DETECTION FAILURE LED TO FALSE-SAFE OUTPUT" if false_safe else None,
        mean_depth_error_m=average(depth_errors),max_depth_error_m=maximum(depth_errors),
        mean_position_error_m=average(position_errors),max_position_error_m=maximum(position_errors),fault_responses=details)
