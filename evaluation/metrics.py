"""Pure prototype evaluation functions; undefined results are None."""
from math import isfinite, hypot


def finite(value):
    return isinstance(value, (int, float)) and isfinite(value)


def absolute_error(estimate, truth):
    return abs(estimate-truth) if finite(estimate) and finite(truth) else None


def depth_error(estimate, truth):
    error = absolute_error(estimate, truth)
    return {"depth_error_m": error, "depth_error_cm": error*100 if error is not None else None}


def detection_outcome(present, detected):
    if present is None or detected is None: return None
    return {(True, True): "TRUE_POSITIVE", (False, False): "TRUE_NEGATIVE",
            (False, True): "FALSE_POSITIVE", (True, False): "FALSE_NEGATIVE"}[(bool(present), bool(detected))]


def average(values):
    values = [v for v in values if finite(v)]
    return sum(values)/len(values) if values else None


def minimum(values):
    values = [v for v in values if finite(v)]
    return min(values) if values else None


def maximum(values):
    values = [v for v in values if finite(v)]
    return max(values) if values else None


def detection_metrics(outcomes):
    """Caller supplies independent experiment outcomes, not repeated frames."""
    counts = {key: outcomes.count(key) for key in ("TRUE_POSITIVE", "TRUE_NEGATIVE", "FALSE_POSITIVE", "FALSE_NEGATIVE")}
    total = sum(counts.values())
    if total < 2: return None
    tp, tn, fp, fn = (counts[k] for k in ("TRUE_POSITIVE", "TRUE_NEGATIVE", "FALSE_POSITIVE", "FALSE_NEGATIVE"))
    ratio = lambda n, d: n/d if d else None
    return dict(counts=counts, precision=ratio(tp,tp+fp), recall=ratio(tp,tp+fn),
        false_positive_rate=ratio(fp,fp+tn), false_negative_rate=ratio(fn,fn+tp), accuracy=ratio(tp+tn,total))


def true_distance(bucket_x, bucket_z, truth):
    if not truth.utility_present or not all(finite(v) for v in (bucket_x,bucket_z,truth.utility_x_m,truth.utility_depth_m)):
        return None
    return hypot(bucket_x-truth.utility_x_m,bucket_z+truth.utility_depth_m)
