import unittest
from evaluation.metrics import depth_error, absolute_error, average, detection_outcome, detection_metrics, minimum

class MetricsTests(unittest.TestCase):
    def test_depth(self):
        result=depth_error(1.36,1.32)
        self.assertAlmostEqual(result["depth_error_m"],.04)
        self.assertAlmostEqual(result["depth_error_cm"],4.)
        self.assertAlmostEqual(absolute_error(4.17,4.20),.03)

    def test_detection(self):
        for present,detected,expected in ((True,True,"TRUE_POSITIVE"),(False,True,"FALSE_POSITIVE"),
                (True,False,"FALSE_NEGATIVE"),(False,False,"TRUE_NEGATIVE")):
            self.assertEqual(detection_outcome(present,detected),expected)
        self.assertIsNone(detection_outcome(True,None))

    def test_missing_average_minimum(self):
        self.assertEqual(average([2,3,4]),3.)
        self.assertEqual(minimum([.5,.2,-.05]),-.05)
        self.assertIsNone(average([None]))
        self.assertIsNone(depth_error(None,1.32)["depth_error_m"])
        self.assertIsNone(average([float("nan")]))

    def test_independent_run_aggregates(self):
        self.assertIsNone(detection_metrics(["TRUE_POSITIVE"]))
        result=detection_metrics(["TRUE_POSITIVE","TRUE_NEGATIVE","FALSE_POSITIVE","FALSE_NEGATIVE"])
        for key in ("precision","recall","accuracy","false_positive_rate","false_negative_rate"):
            self.assertEqual(result[key],.5)
