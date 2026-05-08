"""
ONTINUITY DRIVING SYSTEM - Phase 1 Brainstem v5
================================================
Verified from gym-donkeycar master branch source and examples.
Uses gymnasium + gym_donkeycar 1.3.1.
Simulator must be running with track loaded manually.

Architecture:
- Four sensor pair stubs (forward active, others ready)
- Three phase startup: ORIENTING -> CORRECTING -> TRACKING
- Failure protocol: ASSUME -> STOP
- PID steering from CTE (Cross Track Error)

Phase 1 Goal: Car moves forward and stays centered on the track.
No neural net. No track-specific training. Geometry only.

Changes from original v5:
- Yaw fix: reads from info["car"][2] (was info["yaw"] - always returned 0.0)
- Yaw wraparound fix: handles Unity yaw boundary crossing at +/-180
- Yaw coefficients set to 0.0 pending proper tuning
- MissionState two-loop interface wired in
- Stuck detection and recovery: escapes phantom CTE oscillation
- Hill assist and speed cap for mountain track
- Terrain false positive suppression
- Reflex suppression: don't steer further out of bounds
- Ontinuity outer loop connected
"""

import gymnasium as gym
import sys
import os
from datetime import datetime
import numpy as np
import gym_donkeycar  # noqa: F401 - registers environments
from mission_state import MissionState
from ontinuity_loop import start_ontinuity_loop
from camera_cte import compute_camera_cte

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

SIM_HOST = "127.0.0.1"
SIM_PORT = 9091

PID_P = 2.0
PID_D = 15.0
PID_I = 0.0

THROTTLE_ORIENTING  = 0.15
THROTTLE_CORRECTING = 0.28
THROTTLE_TRACKING   = 0.8

CTE_CORRECTING_THRESHOLD = 0.5
CTE_TRACKING_THRESHOLD   = 0.2
CTE_STOP_THRESHOLD       = 6
STABLE_CYCLES_REQUIRED   = 5

STUCK_SPEED     = 0.15
STUCK_THRESHOLD = 15
STUCK_RECOVERY  = 40

# -----------------------------------------
# STATE
# -----------------------------------------

phase           = "ORIENTING"
prev_cte        = 0.0
integral        = 0.0
stable_cycles   = 0
cycle_count     = 0
yaw_history     = []
prev_yaw        = 0.0
yaw_rate        = 0.0
stuck_cycles    = 0
recovery_cycles = 0
consecutive_obstacle_cycles = 0
lidar_feed      = {"lidar": [], "last_obstacle_steer": 0.0}
mission         = MissionState()

# -----------------------------------------
# PID CONTROLLER
# -----------------------------------------

def compute_steering(cte):
    global prev_cte, integral, yaw_rate
    p         = PID_P * cte
    d         = PID_D * (cte - prev_cte)
    integral += cte
    i         = PID_I * integral
    boost     = 1.0 + (abs(cte) * 2.5) + (yaw_rate * 0.0)
    steer     = -(p + d + i) * boost
    steer     = max(-1.0, min(1.0, steer))
    prev_cte  = cte
    return steer

def get_throttle():
    if phase == "ORIENTING":  return THROTTLE_ORIENTING
    if phase == "CORRECTING": return THROTTLE_CORRECTING
    if phase == "TRACKING":   return THROTTLE_TRACKING
    return 0.0

def advance_phase(cte):
    global phase, stable_cycles
    if phase == "ORIENTING" and abs(cte) < CTE_CORRECTING_THRESHOLD:
        stable_cycles += 1
        if stable_cycles >= STABLE_CYCLES_REQUIRED:
            phase = "CORRECTING"
            stable_cycles = 0
            print("[ODS] Phase: CORRECTING")
    elif phase == "CORRECTING" and abs(cte) < CTE_TRACKING_THRESHOLD:
        stable_cycles += 1
        if stable_cycles >= STABLE_CYCLES_REQUIRED:
            phase = "TRACKING"
            stable_cycles = 0
            print("[ODS] Phase: TRACKING - center acquired")
    else:
        stable_cycles = 0

# -----------------------------------------
# MAIN
# -----------------------------------------

if __name__ == "__main__":
    # SESSION LOGGING - Python tee, UTF-8, bypasses PowerShell encoding
    log_dir = r"C:\donkeycar\sessions"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    log_file = open(log_path, "w", encoding="utf-8")

    class Tee:
        def __init__(self, *streams): self.streams = streams
        def write(self, data):
            for s in self.streams: s.write(data)
        def flush(self):
            for s in self.streams: s.flush()

    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)
    print("[ODS] Ontinuity Driving System - Phase 1 Brainstem v5")
    print("[ODS] Sensor pairs: FORWARD active | LEFT REAR RIGHT ready")
    print(f"[ODS] Connecting to simulator at {SIM_HOST}:{SIM_PORT}")
    print("[ODS] Make sure track is loaded in simulator\n")

    conf = {
        "host": SIM_HOST,
        "port": SIM_PORT,
        "lidar_config": {
            "deg_per_sweep_inc": "2.0",
            "deg_ang_down": "0.0",
            "deg_ang_delta": "-1.0",
            "num_sweeps_levels": "1",
            "max_range": "50.0",
            "noise": "0.4",
            "offset_x": "0.0",
            "offset_y": "0.5",
            "offset_z": "0.5",
            "rot_x": "0.0"
        }
    }

    env = gym.make("donkey-waveshare-v0", conf=conf)

    obs, info = env.reset()
    print("[ODS] Connected. Car reset. Starting drive sequence.")
    print("[ODS] Phase: ORIENTING\n")
    ontinuity_thread = start_ontinuity_loop(mission, lidar_feed)
    print("[ODS] Ontinuity outer loop started\n")

    try:
        while True:
            cycle_count += 1

            # SENSORS
            cte  = info.get("cte", 0.0)
            sim_cte = cte
            yaw  = info.get("car", (0.0, 0.0, 0.0))[2]
            yaw_history.append(yaw)
            if len(yaw_history) > 3:
                yaw_history.pop(0)
            if len(yaw_history) == 3:
                delta = abs(yaw_history[-1] - yaw_history[0])
                if delta > 180.0:
                    delta = 360.0 - delta
                yaw_rate = delta
            else:
                yaw_rate = 0.0
            speed = info.get("speed", 0.0)
            cam_cte = compute_camera_cte(obs)
            cte     = cam_cte

            # TELEMETRY UPDATE
            mission.update(
                cycle_count=cycle_count,
                phase=phase,
                cte=cte,
                yaw_rate=yaw_rate,
                speed=speed,
                forward_vel=info.get("forward_vel", 0.0),
                accel=info.get("accel", (0.0, 0.0, 0.0)),
                lap_count=info.get("lap_count", 0),
                last_lap_time=info.get("last_lap_time", 0.0),
            )

            # PERIODIC LIDAR SUMMARY
            if cycle_count % 20 == 0:
                lidar = info.get('lidar', [])
                if len(lidar) > 0:
                    forward = [lidar[i] for i in list(range(0, 15)) + list(range(165, 180)) if lidar[i] > 0]
                    min_fwd = min(forward) if forward else 99
                    print(f"[ODS] FORWARD MIN: {min_fwd:.2f}m")

            # STUCK DETECTION AND RECOVERY
            if speed < STUCK_SPEED and phase == "TRACKING":
                stuck_cycles += 1
            else:
                stuck_cycles = 0

            if stuck_cycles >= STUCK_THRESHOLD:
                stuck_cycles    = 0
                recovery_cycles = STUCK_RECOVERY
                print(f"[ODS] STUCK DETECTED - speed {speed:.2f} - recovery burst")

            if recovery_cycles > 0:
                recovery_cycles -= 1
                action = np.array([0.0, 0.50])
                obs, reward, terminated, truncated, info = env.step(action)
                if recovery_cycles == 0:
                    print("[ODS] Recovery complete - resuming normal control")
                if terminated or truncated:
                    print("[ODS] Episode ended during recovery - resetting")
                    obs, info                   = env.reset()
                    phase                       = "ORIENTING"
                    prev_cte                    = 0.0
                    integral                    = 0.0
                    stable_cycles               = 0
                    recovery_cycles             = 0
                    stuck_cycles                = 0
                    consecutive_obstacle_cycles = 0
                continue

            # STOP CONDITION
            if abs(cte) >= CTE_STOP_THRESHOLD:
                print(f"[ODS] STOP - CTE {cte:.3f} exceeds threshold")
                mission.record_stop(cycle_count, cte)
                action = np.array([0.0, 0.0])
                env.step(action)
                break

            # STEERING
            steering = compute_steering(cte)

            # OBSTACLE AVOIDANCE
            obstacle_steer = 0.0
            lidar_raw      = info.get('lidar', [])
            lidar_feed["lidar"] = lidar_raw

            if len(lidar_raw) > 0:
                center_right = [lidar_raw[i] for i in range(0, 10)   if lidar_raw[i] > 0]
                center_left  = [lidar_raw[i] for i in range(170, 180) if lidar_raw[i] > 0]
                wide_right   = [lidar_raw[i] for i in range(10, 30)   if lidar_raw[i] > 0]
                wide_left    = [lidar_raw[i] for i in range(150, 170) if lidar_raw[i] > 0]

                min_center_r = min(center_right) if center_right else 99
                min_center_l = min(center_left)  if center_left  else 99
                min_wide_r   = min(wide_right)   if wide_right   else 99
                min_wide_l   = min(wide_left)    if wide_left    else 99

                trigger = False
                if min(min_center_r, min_center_l) < 6.0:
                    trigger        = True
                    obstacle_steer = -1.0 if min_center_r < min_center_l else 1.0
                elif min(min_wide_r, min_wide_l) < 3.0:
                    trigger        = True
                    obstacle_steer = -1.0 if min_wide_r < min_wide_l else 1.0

                # Reflex suppression: don't steer further out of bounds
                if (obstacle_steer > 0 and cte > 1.0) or (obstacle_steer < 0 and cte < -1.0):
                    obstacle_steer = 0.0
                    trigger        = False

                # Update lidar feed for outer loop AFTER all obstacle logic
                lidar_feed["last_obstacle_steer"] = obstacle_steer

                if trigger:
                    consecutive_obstacle_cycles += 1
                    if consecutive_obstacle_cycles > 12:
                        obstacle_steer = 0.0
                    else:
                        print(f"[ODS] OBSTACLE! steering {'LEFT' if obstacle_steer < 0 else 'RIGHT'}")
                else:
                    consecutive_obstacle_cycles = 0

            # THROTTLE AND DIRECTIVES
            throttle   = get_throttle()
            directives = mission.get_directives()
            steering_bias = directives.get("steering_bias", 0.0)
            if steering_bias != 0.0:
                obstacle_steer = 0.0

            if directives["abort"]:
                print("[ODS] ABORT directive received - stopping")
                break

            advance_phase(cte)

            if cycle_count % 20 == 0:
                print(f"[ODS] {phase} | CTE: {cte:.3f} | "
                      f"Steer: {steering:.3f} | "
                      f"Throttle: {throttle:.2f} | "
                      f"Speed: {speed:.2f} | "
                      f"Yaw rate: {yaw_rate:.4f} | "
                      f"CamCTE: {cam_cte:.3f}")
                      

            cte_rate           = abs(cte - prev_cte)
            cte_throttle_scale = max(0.4, 1.0 - (abs(cte) * 0.25) - (cte_rate * 1.0) - (yaw_rate * 0.0))
            scaled_throttle    = throttle * cte_throttle_scale * directives["throttle_ceiling"]

            if phase == "TRACKING" and speed < 0.30:
                hill_assist     = min(0.20, (0.30 - speed) * 0.8)
                scaled_throttle = min(1.0, scaled_throttle + hill_assist)
            elif phase == "TRACKING" and speed > 2.0:
                scaled_throttle = 0.0

            if abs(obstacle_steer) > 0:
                final_steer     = obstacle_steer
                scaled_throttle = scaled_throttle * 0.5
            else:
                final_steer = steering

            # Apply outer loop steering bias
            if steering_bias != 0.0:
                final_steer = max(-1.0, min(1.0, final_steer + steering_bias))

            action = np.array([final_steer, scaled_throttle])
            obs, reward, terminated, truncated, info = env.step(action)

            if terminated or truncated:
                print("[ODS] Episode ended - resetting")
                obs, info                   = env.reset()
                phase                       = "ORIENTING"
                prev_cte                    = 0.0
                integral                    = 0.0
                stable_cycles               = 0
                recovery_cycles             = 0
                stuck_cycles                = 0
                consecutive_obstacle_cycles = 0

    except KeyboardInterrupt:
        print("\n[ODS] Stopped by user")
    finally:
        env.close()
        print("[ODS] Environment closed.")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        log_file.close()
