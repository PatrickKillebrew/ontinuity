"""
ONTINUITY OUTER LOOP - Phase 2 Mission Layer
=============================================
Runs as a daemon thread above the ODS brainstem.
Reads telemetry from MissionState, writes directives back.
The brainstem never calls this directly.

Three-horizon architecture:
- Present horizon: brainstem reflexes (this cycle)
- Near horizon:    directives held ready for brainstem to act on
- Deep horizon:    pattern recognition and reasoning over time (this file)

Current interventions:
1. Gate approach speed management — detects bilateral symmetric obstacle
   signature, drops throttle_ceiling for precise approach.
2. Gate steering bias — speed-aware corrective bias issued at gate detection.
"""

import time
import threading


# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

LOOP_INTERVAL        = 0.10   # seconds between outer loop cycles (~10Hz)
GATE_LIDAR_SYMMETRY  = 2.0    # max L/R distance difference to classify as gate
GATE_TRIGGER_DIST    = 8.0    # distance below this = gate/obstacle zone
GATE_THROTTLE_CAP    = 0.20   # throttle ceiling during gate passage
GATE_HOLD_CYCLES     = 5      # outer loop cycles to hold gate directive after clear

BIAS_STRENGTH        = 0.5    # steering bias magnitude (0.0-1.0)
BIAS_HOLD_CYCLES     = 10     # outer loop cycles to hold steering bias
CTE_BIAS_THRESHOLD   = 0.5    # CTE above this = car is meaningfully displaced


# -----------------------------------------
# OUTER LOOP STATE
# -----------------------------------------

class OuterLoopState:
    def __init__(self):
        self.gate_active      = False
        self.gate_hold_count  = 0
        self.bias_active      = False
        self.bias_hold_count  = 0
        self.bias_direction   = 0.0
        self.intervention_log = []

    def log(self, event):
        entry = f"[ONTINUITY] {event}"
        self.intervention_log.append(entry)
        print(entry)


# -----------------------------------------
# PATTERN DETECTION
# -----------------------------------------

def F(lidar):
    """
    Returns (is_gate, symmetry, min_r, min_l) from raw lidar array.
    Gate signature: two objects roughly equidistant left and right at short range.
    """
    if lidar is None or len(lidar) < 180:
        return False, 99.0, 99.0, 99.0

    center_right = [lidar[i] for i in range(0, 10)   if lidar[i] > 0]
    center_left  = [lidar[i] for i in range(170, 180) if lidar[i] > 0]

    min_r = min(center_right) if center_right else 99.0
    min_l = min(center_left)  if center_left  else 99.0

    if min_r > GATE_TRIGGER_DIST and min_l > GATE_TRIGGER_DIST:
        return False, 99.0, min_r, min_l

    symmetry = abs(min_r - min_l)
    is_gate  = symmetry < GATE_LIDAR_SYMMETRY and min(min_r, min_l) < GATE_TRIGGER_DIST

    return is_gate, symmetry, min_r, min_l


def compute_steering_bias(cte, obstacle_steer, min_r, min_l, bias_strength=BIAS_STRENGTH):
    """
    Compute a corrective steering bias when the brainstem is heading
    the wrong direction at a gate or obstacle.
    bias_strength is speed-scaled by the caller.
    """
    if min_r < 99.0 or min_l < 99.0:
        obstacle_on_right = min_r < min_l
        obstacle_on_left  = min_l < min_r

        if obstacle_on_right and abs(min_r - min_l) > 0.2:
            strength = bias_strength + (max(0, cte) * 0.2)
            return -min(1.0, strength)

        if obstacle_on_left and abs(min_r - min_l) > 0.2:
            strength = bias_strength + (max(0, -cte) * 0.2)
            return min(1.0, strength)

    if cte > CTE_BIAS_THRESHOLD and obstacle_steer >= 0:
        return -bias_strength

    if cte < -CTE_BIAS_THRESHOLD and obstacle_steer <= 0:
        return bias_strength

    return 0.0


# -----------------------------------------
# MAIN OUTER LOOP
# -----------------------------------------

def run_ontinuity_loop(mission, lidar_feed):
    """
    Main outer loop function. Run as a daemon thread.
    """
    state = OuterLoopState()
    state.log("Outer loop started")

    while True:
        time.sleep(LOOP_INTERVAL)

        try:
            snapshot  = mission.get_telemetry_snapshot()
            lidar     = lidar_feed.get("lidar", [])
            obs_steer = lidar_feed.get("last_obstacle_steer", 0.0)
            cte       = snapshot.get("cte", 0.0)
            speed     = snapshot.get("speed", 1.0)
            phase     = snapshot.get("phase", "ORIENTING")

            # Only intervene during TRACKING
            if phase != "TRACKING":
                mission.set_directives(throttle_ceiling=1.0, steering_bias=0.0)
                state.gate_active     = False
                state.gate_hold_count = 0
                state.bias_active     = False
                state.bias_hold_count = 0
                continue

            # ── GATE / OBSTACLE DETECTION ──────────────────────────
            #is_gate, symmetry, min_r, min_l = detect_gate_signature(lidar)
            is_gate = False
            if is_gate and not state.gate_active:
                state.gate_active     = True
                state.gate_hold_count = 0
                state.log(f"GATE DETECTED — symmetry {symmetry:.2f}m "
                          f"R:{min_r:.1f}m L:{min_l:.1f}m CTE:{cte:.2f} "
                          f"— throttle_ceiling → {GATE_THROTTLE_CAP}")
                mission.set_directives(throttle_ceiling=GATE_THROTTLE_CAP)

                #Speed-aware steering bias
                # speed_factor         = max(0.3, 1.0 - (speed * 0.15))
                # scaled_bias_strength = BIAS_STRENGTH * speed_factor
                # scaled_hold          = max(3, int(BIAS_HOLD_CYCLES * speed_factor))
                # bias = compute_steering_bias(cte, obs_steer, min_r, min_l, scaled_bias_strength)

                # if bias != 0.0:
                    # direction = "LEFT" if bias < 0 else "RIGHT"
                    # state.log(f"STEERING BIAS {direction} {abs(bias):.2f} — "
                              # f"obs_steer:{obs_steer:.1f} CTE:{cte:.2f} "
                              # f"speed_factor:{speed_factor:.2f}")
                    # state.bias_active     = True
                    # state.bias_hold_count = scaled_hold
                    # state.bias_direction  = bias
                    # mission.set_directives(steering_bias=bias)

            elif state.gate_active:
                if not is_gate:
                    state.gate_hold_count += 1
                    if state.gate_hold_count >= GATE_HOLD_CYCLES:
                        state.gate_active     = False
                        state.gate_hold_count = 0
                        state.log("GATE CLEARED — throttle_ceiling restored")
                        mission.set_directives(throttle_ceiling=1.0)

            # ── STEERING BIAS HOLD AND RELEASE ─────────────────────
            if state.bias_active:
                state.bias_hold_count -= 1
                if state.bias_hold_count <= 0:
                    state.bias_active    = False
                    state.bias_direction = 0.0
                    state.log("STEERING BIAS released")
                    mission.set_directives(steering_bias=0.0)

        except Exception as e:
            print(f"[ONTINUITY] Outer loop error: {e}")


# -----------------------------------------
# LAUNCH HELPER
# -----------------------------------------

def start_ontinuity_loop(mission, lidar_feed):
    """
    Launch the outer loop as a daemon thread.
    Returns the thread object.
    """
    t = threading.Thread(
        target=run_ontinuity_loop,
        args=(mission, lidar_feed),
        daemon=True
    )
    t.start()
    return t
