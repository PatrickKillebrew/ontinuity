"""
ONTINUITY OUTER LOOP — Three Horizon Architecture
==================================================
Deep Horizon:    ~5Hz  — trend detection, curve prediction, confidence scoring
Near Horizon:    ~10Hz — event validation, directive commitment, lifecycle management
Present Horizon: brainstem (ods_phase1_v5.py) — reflexes only

ALL sensor interpretation is from the car's perspective. Always.

LiDAR layout (confirmed from brainstem, car's perspective):
  RIGHT side of car: indices   0–35   (center-right 0-10, wide-right 10-30)
  LEFT  side of car: indices 145–180  (wide-left 150-170, center-left 170-180)
  FORWARD (center):  indices   0–15 + 165–180

RIGHT curve signature (car's perspective):
  — LEFT channel CLOSES  : left wall curving in toward the car's forward path
  — RIGHT channel OPENS  : right wall dropping away, revealing the corridor
  — CENTER eventually closes as the left wall sweeps across the forward arc
  — Action: steer RIGHT into the opening right corridor

LEFT curve signature (car's perspective):
  — RIGHT channel CLOSES : right wall curving in toward the car's forward path
  — LEFT channel OPENS   : left wall dropping away, revealing the corridor
  — CENTER eventually closes as the right wall sweeps across the forward arc
  — Action: steer LEFT into the opening left corridor

Horizon time boundaries:
  DEEP_ENTRY     = 3.0s  deep starts watching and building confidence
  NEAR_ENTRY     = 1.5s  near commits and issues directive
  PRESENT_OWN    = 0.2s  brainstem owns completely, no overrides

Event lifecycle:
  NONE -> OPEN (deep confident) -> ACTIVE (near committed) -> CLOSED (curve done)
"""

import time
import threading
import traceback
from collections import deque


# ─────────────────────────────────────────
# TIME HORIZON BOUNDARIES (seconds)
# ─────────────────────────────────────────

DEEP_ENTRY   = 3.0   # deep starts watching
NEAR_ENTRY   = 1.5   # near commits and directs
PRESENT_OWN  = 0.2   # brainstem sovereign

# ─────────────────────────────────────────
# LOOP RATES
# ─────────────────────────────────────────

DEEP_INTERVAL = 0.20   # ~5Hz
NEAR_INTERVAL = 0.10   # ~10Hz

# ─────────────────────────────────────────
# LiDAR CHANNEL INDICES (car's perspective)
# ─────────────────────────────────────────

CH_LEFT    = list(range(145, 180))
CH_RIGHT   = list(range(0, 35))
CH_CENTER  = list(range(0, 15)) + list(range(165, 180))

# ─────────────────────────────────────────
# DEEP HORIZON TUNING
# ─────────────────────────────────────────

DEEP_HISTORY      = 8
CONF_THRESHOLD    = 0.25
CLOSE_SLOPE_MIN   = 0.05
OPEN_SLOPE_MAX    = 0.05
MAX_CLOSE_RATE    = 1.5

# ─────────────────────────────────────────
# NEAR HORIZON TUNING
# ─────────────────────────────────────────

BASE_BIAS     = 0.28
MAX_BIAS      = 0.50
BASE_THROTTLE = 0.80
MIN_THROTTLE  = 0.55
CURVE_DONE_OPEN  = 6.0
CURVE_DONE_CLOSE = 4.0


# ─────────────────────────────────────────
# SHARED EVENT STATE
# ─────────────────────────────────────────

class EventState:
    def __init__(self):
        self._lock         = threading.Lock()
        self.event_type    = "NONE"
        self.lifecycle     = "NONE"
        self.confidence    = 0.0
        self.tta           = 99.0
        self.severity      = 0.0
        self.steering_bias = 0.0
        self.throttle_cap  = 1.0
        self.cte_delta     = 0.0
        self.steer_applied = 0.0
        self.reflex_fired  = False

    def open_event(self, etype, conf, tta, severity):
        with self._lock:
            self.event_type = etype
            self.lifecycle  = "OPEN"
            self.confidence = conf
            self.tta        = tta
            self.severity   = severity

    def activate(self, bias, throttle):
        with self._lock:
            self.lifecycle     = "ACTIVE"
            self.steering_bias = bias
            self.throttle_cap  = throttle

    def close(self):
        with self._lock:
            self.lifecycle     = "CLOSED"
            self.event_type    = "NONE"
            self.steering_bias = 0.0
            self.throttle_cap  = 1.0

    def reset(self):
        with self._lock:
            self.lifecycle     = "NONE"
            self.event_type    = "NONE"
            self.confidence    = 0.0
            self.tta           = 99.0
            self.severity      = 0.0
            self.steering_bias = 0.0
            self.throttle_cap  = 1.0

    def set_tta(self, tta):
        with self._lock:
            self.tta = tta

    def snapshot(self):
        with self._lock:
            return {
                "event_type":    self.event_type,
                "lifecycle":     self.lifecycle,
                "confidence":    self.confidence,
                "tta":           self.tta,
                "severity":      self.severity,
                "steering_bias": self.steering_bias,
                "throttle_cap":  self.throttle_cap,
            }

    def write_feedback(self, cte_delta, steer_applied, reflex_fired):
        with self._lock:
            self.cte_delta     = cte_delta
            self.steer_applied = steer_applied
            self.reflex_fired  = reflex_fired


# ─────────────────────────────────────────
# SHARED CHANNEL READER
# ─────────────────────────────────────────

def read_channels(lidar):
    """
    Returns (min_left, min_center, min_right) as plain Python floats.
    99.0 = no return = open/clear.
    All values from the car's perspective.
    """
    if lidar is None or len(lidar) < 180:
        return 99.0, 99.0, 99.0

    left   = [float(lidar[i]) for i in CH_LEFT   if float(lidar[i]) > 0.0]
    center = [float(lidar[i]) for i in CH_CENTER  if float(lidar[i]) > 0.0]
    right  = [float(lidar[i]) for i in CH_RIGHT   if float(lidar[i]) > 0.0]

    return (
        min(left)   if left   else 99.0,
        min(center) if center else 99.0,
        min(right)  if right  else 99.0,
    )


# ─────────────────────────────────────────
# TREND ANALYSIS
# ─────────────────────────────────────────

def trend_slope(history):
    """
    Rate of change (m/cycle). Positive = wall closing toward car.
    """
    n = len(history)
    if n < 4:
        return 0.0
    half     = n // 2
    h        = list(history)
    mean_old = sum(h[:half])  / half
    mean_new = sum(h[half:])  / (n - half)
    return float(mean_old - mean_new) / float(half)


def curve_confidence(closing_slope, opening_slope, n):
    if closing_slope < CLOSE_SLOPE_MIN:
        return 0.0
    close_strength = min(1.0, closing_slope / MAX_CLOSE_RATE)
    open_bonus     = 0.20 if opening_slope < OPEN_SLOPE_MAX else 0.0
    history_scale  = min(1.0, n / DEEP_HISTORY)
    return min(1.0, float((close_strength + open_bonus) * history_scale))


# ─────────────────────────────────────────
# DEEP HORIZON (~5Hz)
# ─────────────────────────────────────────

def run_deep_horizon(mission, lidar_feed, ev):
    left_h   = deque(maxlen=DEEP_HISTORY)
    center_h = deque(maxlen=DEEP_HISTORY)
    right_h  = deque(maxlen=DEEP_HISTORY)

    print("[DEEP] Deep horizon started")

    while True:
        time.sleep(DEEP_INTERVAL)
        try:
            snap  = mission.get_telemetry_snapshot()
            phase = snap.get("phase", "ORIENTING")
            speed = max(float(snap.get("speed", 0.1)), 0.1)
            lidar = lidar_feed.get("lidar", [])

            if phase != "TRACKING":
                left_h.clear(); center_h.clear(); right_h.clear()
                if ev.lifecycle != "NONE":
                    ev.reset()
                continue

            min_l, min_c, min_r = read_channels(lidar)
            left_h.append(min_l)
            center_h.append(min_c)
            right_h.append(min_r)

            tta = float(min_c / speed)
            ev.set_tta(tta)

            if tta > DEEP_ENTRY:
                if ev.lifecycle == "OPEN":
                    ev.close()
                continue

            n           = len(left_h)
            left_slope  = trend_slope(left_h)
            right_slope = trend_slope(right_h)

            # RIGHT CURVE: left wall closing + right wall opening
            right_conf = curve_confidence(
                closing_slope=left_slope,
                opening_slope=right_slope,
                n=n
            )

            # LEFT CURVE: right wall closing + left wall opening
            left_conf = curve_confidence(
                closing_slope=right_slope,
                opening_slope=left_slope,
                n=n
            )

            current = ev.snapshot()

            if right_conf >= left_conf and right_conf >= CONF_THRESHOLD:
                sev = min(1.0, float(left_slope / MAX_CLOSE_RATE))
                if current["lifecycle"] in ("NONE", "CLOSED"):
                    ev.open_event("RIGHT_CURVE", right_conf, tta, sev)
                    print(f"[DEEP] RIGHT_CURVE OPEN  conf:{right_conf:.2f} "
                          f"tta:{tta:.1f}s sev:{sev:.2f} "
                          f"L:{min_l:.1f}m R:{min_r:.1f}m C:{min_c:.1f}m")

            elif left_conf >= CONF_THRESHOLD:
                sev = min(1.0, float(right_slope / MAX_CLOSE_RATE))
                if current["lifecycle"] in ("NONE", "CLOSED"):
                    ev.open_event("LEFT_CURVE", left_conf, tta, sev)
                    print(f"[DEEP] LEFT_CURVE OPEN  conf:{left_conf:.2f} "
                          f"tta:{tta:.1f}s sev:{sev:.2f} "
                          f"L:{min_l:.1f}m R:{min_r:.1f}m C:{min_c:.1f}m")

            else:
                if current["lifecycle"] == "OPEN":
                    ev.close()
                    print("[DEEP] Event candidate cleared")

        except Exception as e:
            print(f"[DEEP] Error: {e}")
            traceback.print_exc()


# ─────────────────────────────────────────
# NEAR HORIZON (~10Hz)
# ─────────────────────────────────────────

def run_near_horizon(mission, lidar_feed, ev):
    last_lifecycle  = "NONE"
    last_event_type = "NONE"

    print("[NEAR] Near horizon started")

    while True:
        time.sleep(NEAR_INTERVAL)
        try:
            snap  = mission.get_telemetry_snapshot()
            phase = snap.get("phase", "ORIENTING")
            speed = max(float(snap.get("speed", 0.1)), 0.1)
            lidar = lidar_feed.get("lidar", [])

            if phase != "TRACKING":
                mission.set_directives(
                    steering_bias=0.0,
                    throttle_ceiling=1.0,
                    event_type="NONE",
                    event_lifecycle="NONE"
                )
                last_lifecycle  = "NONE"
                last_event_type = "NONE"
                continue

            min_l, min_c, min_r = read_channels(lidar)
            tta = float(min_c / speed)
            ev.set_tta(tta)

            current = ev.snapshot()

            # PRESENT SOVEREIGN: below 0.2s brainstem owns it
            if tta < PRESENT_OWN:
                mission.set_directives(
                    steering_bias=float(current["steering_bias"]),
                    throttle_ceiling=float(current["throttle_cap"]),
                    event_type=current["event_type"],
                    event_lifecycle=current["lifecycle"]
                )
                continue

            # OPEN EVENT: commit when TTA enters near horizon window
            if current["lifecycle"] == "OPEN" and tta < NEAR_ENTRY:
                sev      = float(current["severity"])
                bias     = min(MAX_BIAS, BASE_BIAS * (1.0 + sev))
                throttle = max(MIN_THROTTLE, BASE_THROTTLE - (sev * 0.25))

                if current["event_type"] == "RIGHT_CURVE":
                    ev.activate(float(bias), float(throttle))
                    print(f"[NEAR] RIGHT_CURVE ACTIVE  "
                          f"bias:+{bias:.2f} throttle:{throttle:.2f} "
                          f"tta:{tta:.1f}s L:{min_l:.1f}m R:{min_r:.1f}m")

                elif current["event_type"] == "LEFT_CURVE":
                    ev.activate(float(-bias), float(throttle))
                    print(f"[NEAR] LEFT_CURVE ACTIVE  "
                          f"bias:{-bias:.2f} throttle:{throttle:.2f} "
                          f"tta:{tta:.1f}s L:{min_l:.1f}m R:{min_r:.1f}m")

            # ACTIVE EVENT: hold directive, check for completion
            elif current["lifecycle"] == "ACTIVE":
                done = False

                if current["event_type"] == "RIGHT_CURVE":
                    done = bool(
                        min_r > CURVE_DONE_OPEN and
                        min_l > CURVE_DONE_CLOSE and
                        tta > NEAR_ENTRY
                    )
                elif current["event_type"] == "LEFT_CURVE":
                    done = bool(
                        min_l > CURVE_DONE_OPEN and
                        min_r > CURVE_DONE_CLOSE and
                        tta > NEAR_ENTRY
                    )

                if done:
                    ev.close()
                    print(f"[NEAR] {current['event_type']} CLOSED — "
                          f"corridor confirmed L:{min_l:.1f}m R:{min_r:.1f}m")

            # NO ACTIVE EVENT: obstacle detection only
            elif current["lifecycle"] in ("NONE", "CLOSED"):
                obs_bias     = 0.0
                obs_throttle = 1.0

                if min_l < 3.0 and min_r > min_l * 2.0:
                    obs_bias     =  0.25
                    obs_throttle =  0.80
                elif min_r < 3.0 and min_l > min_r * 2.0:
                    obs_bias     = -0.25
                    obs_throttle =  0.80

                with ev._lock:
                    ev.steering_bias = obs_bias
                    ev.throttle_cap  = obs_throttle

            # ISSUE DIRECTIVE TO BRAINSTEM
            current = ev.snapshot()
            mission.set_directives(
                steering_bias=float(current["steering_bias"]),
                throttle_ceiling=float(current["throttle_cap"]),
                event_type=current["event_type"],
                event_lifecycle=current["lifecycle"]
            )

            if (current["lifecycle"] != last_lifecycle or
                    current["event_type"] != last_event_type):
                last_lifecycle  = current["lifecycle"]
                last_event_type = current["event_type"]

        except Exception as e:
            print(f"[NEAR] Error: {e}")
            traceback.print_exc()


# ─────────────────────────────────────────
# LAUNCH HELPER
# ─────────────────────────────────────────

def start_ontinuity_loop(mission, lidar_feed):
    ev = EventState()

    deep_thread = threading.Thread(
        target=run_deep_horizon,
        args=(mission, lidar_feed, ev),
        daemon=True
    )
    near_thread = threading.Thread(
        target=run_near_horizon,
        args=(mission, lidar_feed, ev),
        daemon=True
    )

    deep_thread.start()
    near_thread.start()

    print("[ONTINUITY] Three horizon architecture active")
    return deep_thread, near_thread
