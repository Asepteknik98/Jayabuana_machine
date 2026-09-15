# XCMG SafeDig AI Copilot

**SEE BELOW ? DIG RIGHT ? STAY ALERT**

MVP-0 is an offline, AI-assisted excavation safety engineering prototype. It demonstrates utility-aware excavation geometry, uncertainty handling, operator context, and software recommendations. It is not a certified safety system.

## Main modules and architecture

- **SafeDig Vision:** simulated subsurface responses, possible utility estimates, confidence, and protective envelope.
- **SafeDig Precision:** simulated bucket movement, depth/width/slope targets, velocity, and planned excavation conflict.
- **SafeDig Guardian:** live webcam or explicitly labelled simulated operator fatigue/attention estimates.

```text
Vision + Precision + Guardian
             ?
         SafeDigState
             ?
        Sensor Fusion
             ?
         Risk Engine
             ?
       Decision Engine
             ?
             HMI
```

Source-neutral states separate sensing adapters from assessment. Risk levels (`SAFE`, `CAUTION`, `HIGH`, `CRITICAL`) and recommended actions (`NORMAL`, `WARN`, `SLOW`, `VERIFY`, `RESTRICT`) are distinct. Missing or weak evidence does not automatically mean SAFE. Ground Truth belongs only to simulation/evaluation; it never feeds Risk or Decision directly.

## Installation

Recommended Python: **3.11**, on Windows 10/11. The final workspace was tested with Python **3.14.6**, PySide6 6.11.2, OpenCV contrib 5.0.0.93, MediaPipe 1.0.1, and NumPy 2.5.3. Python 3.11 was not separately tested in this workspace. Requirements remain unpinned; the versions above describe the tested environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Without shell activation, use `.\.venv\Scripts\python main.py`. Dependency installation requires network access; ordinary demo runs work offline. `opencv-contrib-python` supplies `cv2` and matches MediaPipe's dependency; do not also install a second OpenCV wheel. Tests use standard-library `unittest`, so pytest is not required.

The local MediaPipe model is `models/face_landmarker/face_landmarker.task`; provenance is documented in `models/README.md`. A missing model disables face analysis gracefully. It does not prevent the synthetic demo from running.

## Competition demo

The application opens in **PRESENTATION MODE**, with **Critical Multimodal Demo** and **DEMO MODE** selected, at an idle baseline. Click **START** once.

The approximately 40-second sequence progresses through anomaly, possible utility, design conflict, approaching envelope, increasing fatigue, HIGH/CRITICAL risk, and RESTRICT. Outputs are calculated by the existing engines from deterministic inputs; final risk/action are not scripted. **PAUSE** freezes simulation time; **RESUME** continues. **RESET** returns all current demo and experiment state to baseline, while preserving exported files. Starting again creates a unique experiment ID.

Presentation Mode emphasizes domain summaries, sources, confidence, risk, action, timeline, and system health. **ENGINEERING MODE** exposes the detailed panels and reliability scenarios. Switching the display mode does not change inputs or assessment. The **Experiment Summary** tab shows evaluation results after a run, with **GROUND TRUTH - SIMULATION ONLY** clearly labelled.

## Live Guardian

Choose **LIVE MODE** to open the webcam configured by `CAMERA_INDEX` in `config/camera_config.py`. The worker owns one camera and one face-landmark model. Switching to DEMO releases the worker; returning to LIVE starts it again. **RETRY CAMERA** is available in Engineering Mode.

Changing DEMO/LIVE aborts the current experiment and resets its inputs; a running scenario restarts as a new session with consistent source metadata. Guardian faults do not overwrite live observations. When the camera, face, or analysis is unavailable, fatigue is UNKNOWN and its risk weight is omitted. Vision and Precision continue. Live camera hardware was not exercised in the final automated regression; offline/reconnect/cleanup paths were tested.

## Experiments and reliability

Outputs are created automatically under `output/experiments/<experiment_id>/`:

- `metadata.json`: version, scenario inputs/hash, seed, source selection, and evaluation-only truth.
- `events.json`: meaningful state/fault transitions rather than per-frame messages.
- `telemetry.csv`: scalar snapshots at 2 Hz, plus the final sample.
- `metrics.json` and `summary.json`: detection outcome, depth/position error, proximity, risk/action timing, derived Guardian statistics, compute latency, and reliability checks.

Missing values use JSON null / CSV blanks. No webcam image, video, or raw landmark history is recorded. Risk/Decision latency uses a high-resolution wall clock and is labelled **PROTOTYPE SOFTWARE LATENCY**. Duration metrics use simulation time, excluding pause time.

Single-run detection outcome means at least one reported detection during available observations, not frame-level accuracy. An undiscovered simulated utility can therefore produce FALSE_NEGATIVE or an evaluation-only false-safe flag. These findings do not alter real-time outputs. Aggregation accepts independent completed experiment outcomes; repeated frames are not independent trials. Zero denominators return unavailable values. Fault scenarios cover degradation, offline/stale inputs, false positives/negatives, drift, noise, Guardian loss, and recovery. Fault severity is distinct from Risk Level.

`output/logs/` contains bounded lifecycle logging; `output/screenshots/` is prepared for manual use. Output write failures show a recording error while the demo remains usable. Closing the app stops timers/workers, releases the camera, and finalizes an unfinished experiment as ABORTED.

## Validation

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python -m pip check
```

Tests do not require physical sensors or a webcam. Startup validates consequential risk, clearance, simulation, and freshness parameters. Invalid configuration produces an explicit error rather than silently running assessment.

## Safety disclaimer

XCMG SafeDig AI Copilot is an engineering prototype. Subsurface sensing in MVP-0 is simulated. Machine telemetry is simulated. Webcam Guardian may use live camera input. Risk and Decision outputs are prototype software recommendations.

**This software must NOT be used to control real excavation equipment. RESTRICT does NOT actuate hydraulic control. Automatic stop is NOT implemented.**

Real deployment requires sensor validation, field validation, functional safety engineering, machine integration validation, and regulatory/operational approval. The prototype does not guarantee utility detection or prevention of damage and does not provide a medical fatigue diagnosis.

## Known limitations

- MVP-0 uses simulated GPR/subsurface input; utility classification is a prototype heuristic.
- Excavation/envelope geometry is simplified 2D; slope is retained as a target parameter rather than a terrain model.
- Guardian fatigue is non-medical estimation requiring operator/camera calibration.
- Risk weights and thresholds are prototype calibration parameters.
- Reliability results characterize the configured simulation, not production accuracy or certified response times.
- Real sensor validation is future work; physical machine control is intentionally absent.

## Future work ? not implemented

- **MVP-1:** physical EMI/inductive sensing via a sensor adapter.
- **MVP-2:** moving bucket and physical sensor integration.
- **MVP-3:** real GPR controlled field validation.
- Later research: utility digital twins, physical machine integration, functional safety certification, and CAN/HMI integration.

MVP-0 software prototype only. Do not start MVP-1 without a separate development instruction.
