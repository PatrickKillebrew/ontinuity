"""
ONTINUITY OUTER LOOP - Near Horizon Mission Layer
==================================================
Three-channel situational awareness for corridor navigation.

Channel architecture:
- RIGHT channel:  right-side LiDAR clearance + closing rate
- CENTER channel: forward LiDAR clearance + closing rate
- LEFT channel:   left-side LiDAR clearance + closing rate

Pattern detection:
- Curve: forward closing + asymmetric side closure → steer into curve
- Obstacle: blocked channel → route to clear channel
- Combined: cone + curve → inside curve channel preferred

Directives issued via MissionState:
- steering_bias:    added to brainstem final_steer each cycle
- throttle_ceiling: multiplier on scaled_throttle
"""

import time
import threading
from collections import deque


# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

LOOP_INTERVAL = 0.10   # seconds (~10Hz)

# Channel LiDAR index ranges
CH_RIGHT_INDICES  = list(range(5, 35))
CH_CENTER_INDICES = list(range(0, 15)) + list(range(165, 180))
CH_LEFT_INDICES   = list(range(145, 175))

# Channel thresholds
CH_BLOCKED_DIST        = 3.5   # meters — channel blocked
CH_CLOSING_DIST        = 9.0   # meters — channel in closing zone
CLOSING_RATE_THRESHOLD = 0.4   # meters per 3-cycle window — closing fast
HISTORY_LEN            = 5     # cycles to keep per channel

# Directive strengths
CURVE_STEER_BIAS      = 0.30   # bias added to camera CTE in curve
OBSTACLE_STEER_BIAS   = 0.40   # bias when routing around obstacle
CURVE_THROTTLE_CAP    = 0.80   # throttle ceiling in curve
OBSTACLE_THROTTLE_CAP = 0.80   # throttle ceiling routing around obstacle


# -----------------------------------------
# STATE
# -----------------------------------------

class OuterLoopState:
    def __init__(self):
        self.right_history  = deque(maxlen=HISTORY_LEN)
        self.center_history = deque(maxlen=HISTORY_LEN)
        self.left_history   = deque(maxlen=HISTORY_LEN)
        self.last_situation = "CLEAR"

    def log(self, event):
        print(f"[ONTINUITY] {event}")


# -----------------------------------------
# CHANNEL SENSING
# -----------------------------------------

def read_channels(lidar):
    """Returns (min_r, min_c, min_l) — minimum clearance per channel. 99 = clear."""
    if not lidar or len(lidar) < 180:
        return 99.0, 99.0, 99.0

    right  = [lidar[i] for i in CH_RIGHT_INDICES  if lidar[i] > 0]
    center = [lidar[i] for i in CH_CENTER_INDICES if lidar[i] > 0]
    left   = [lidar[i] for i in CH_LEFT_INDICES   if lidar[i] > 0]

    return (
        min(right)  if right  else 99.0,
        min(center) if center else 99.0,
        min(left)   if left   else 99.0,
    )


def closing_rate(history):
    """Positive = wall approaching. Uses oldest vs newest over 3-cycle window."""
    if len(history) < 3:
        return 0.0
    return history[-3] - history[-1]


# -----------------------------------------
# CHANNEL DECISION
# -----------------------------------------

def compute_channel_directive(state, min_r, min_c, min_l):
    """Returns (situation, steering_bias, throttle_cap)."""

    state.right_history.append(min_r)
    state.center_history.append(min_c)
    state.left_history.append(min_l)

    rate_r = closing_rate(state.right_history)
    rate_c = closing_rate(state.center_history)
    rate_l = closing_rate(state.left_history)

    r_blocked = min_r < CH_BLOCKED_DIST
    c_blocked = min_c < CH_BLOCKED_DIST
    l_blocked = min_l < CH_BLOCKED_DIST
    c_closing = rate_c > CLOSING_RATE_THRESHOLD and min_c < CH_CLOSING_DIST

    # ── CURVE DETECTION ──────────────────────────────────────────
    if c_closing:
        right_curve = rate_r > CLOSING_RATE_THRESHOLD and min_r < min_l
        left_curve  = rate_l > CLOSING_RATE_THRESHOLD and min_l < min_r

        if right_curve and not r_blocked:
            return "RIGHT_CURVE", CURVE_STEER_BIAS, CURVE_THROTTLE_CAP

        if left_curve and not l_blocked:
            return "LEFT_CURVE", -CURVE_STEER_BIAS, CURVE_THROTTLE_CAP

    # ── OBSTACLE ROUTING ─────────────────────────────────────────
    if c_blocked:
        if not r_blocked and (min_r >= min_l or l_blocked):
            return "ROUTE_RIGHT", OBSTACLE_STEER_BIAS, OBSTACLE_THROTTLE_CAP
        elif not l_blocked:
            return "ROUTE_LEFT", -OBSTACLE_STEER_BIAS, OBSTACLE_THROTTLE_CAP

    if r_blocked and not c_blocked:
        return "AVOID_RIGHT", -OBSTACLE_STEER_BIAS * 0.5, OBSTACLE_THROTTLE_CAP
    if l_blocked and not c_blocked:
        return "AVOID_LEFT",  OBSTACLE_STEER_BIAS * 0.5, OBSTACLE_THROTTLE_CAP

    # ── CLEAR ────────────────────────────────────────────────────
    return "CLEAR", 0.0, 1.0


# -----------------------------------------
# MAIN OUTER LOOP
# -----------------------------------------

def run_ontinuity_loop(mission, lidar_feed):
    state = OuterLoopState()
    state.log("Outer loop started — channel architecture active")

    while True:
        time.sleep(LOOP_INTERVAL)

        try:
            snapshot = mission.get_telemetry_snapshot()
            phase    = snapshot.get("phase", "ORIENTING")
            lidar    = lidar_feed.get("lidar", [])

            if phase != "TRACKING":
                mission.set_directives(steering_bias=0.0, throttle_ceiling=1.0)
                state.right_history.clear()
                state.center_history.clear()
                state.left_history.clear()
                state.last_situation = "CLEAR"
                continue

            min_r, min_c, min_l = read_channels(lidar)
            situation, bias, throttle_cap = compute_channel_directive(
                state, min_r, min_c, min_l
            )

            if situation != state.last_situation:
                state.log(
                    f"{situation} — "
                    f"R:{min_r:.1f}m C:{min_c:.1f}m L:{min_l:.1f}m "
                    f"bias:{bias:+.2f} throttle:{throttle_cap:.2f}"
                )
                state.last_situation = situation

            mission.set_directives(
                steering_bias=bias,
                throttle_ceiling=throttle_cap
            )

        except Exception as e:
            print(f"[ONTINUITY] Outer loop error: {e}")


# -----------------------------------------
# LAUNCH HELPER
# -----------------------------------------

def start_ontinuity_loop(mission, lidar_feed):
    t = threading.Thread(
        target=run_ontinuity_loop,
        args=(mission, lidar_feed),
        daemon=True
    )
    t.start()
    return t