"""
MISSION STATE — ODS Phase 2
============================
Thread-safe shared state between the ODS brainstem (inner loop, ~20Hz)
and the Ontinuity mission layer (outer loop, lap-cadence).

Brainstem writes telemetry. Mission layer reads telemetry, writes directives.
Brainstem reads directives each cycle. No blocking in either direction.
"""

import threading
import time
from collections import deque


class MissionState:
    def __init__(self, cte_history_len=100):
        self._lock = threading.Lock()

        # ── Telemetry (brainstem → mission layer) ──────────────────────
        self.telemetry = {
            "phase":              "ORIENTING",
            "cycle_count":        0,
            "cte":                0.0,
            "cte_history":        deque(maxlen=cte_history_len),
            "yaw_rate":           0.0,
            "speed":              0.0,
            "forward_vel":        0.0,
            "accel":              (0.0, 0.0, 0.0),
            "lap_count":          0,
            "last_lap_time":      None,
            "lap_times":          [],          # all completed lap times
            "obstacle_events":    [],          # (cycle, zone, distance)
            "accel_spike_events": [],          # (cycle, magnitude)
            "stop_events":        [],          # (cycle, cte) — CTE threshold hits
            "hit_events":         [],          # (cycle, object)
        }

        # ── Directives (mission layer → brainstem) ─────────────────────
        self.directives = {
            "throttle_ceiling":      1.0,   # cap on scaled_throttle
            "aggressiveness":        1.0,   # multiplier on boost factor
            "obstacle_sensitivity":  1.0,   # multiplier on LiDAR thresholds
            "strategy":              "NORMAL",  # NORMAL | CAUTIOUS | AGGRESSIVE
            "abort":                 False,
            "steering_bias":     0.0,    # outer loop steering correction
        }

        # ── Mission layer internal ─────────────────────────────────────
        self._last_lap_count = 0

    # ── Write API (called by brainstem, hot path) ──────────────────────

    def update(self, cycle_count, phase, cte, yaw_rate, speed,
               forward_vel, accel, lap_count, last_lap_time,
               obstacle_event=None, hit=None):
        with self._lock:
            t = self.telemetry
            t["cycle_count"]  = cycle_count
            t["phase"]        = phase
            t["cte"]          = cte
            t["cte_history"].append(cte)
            t["yaw_rate"]     = yaw_rate
            t["speed"]        = speed
            t["forward_vel"]  = forward_vel
            t["accel"]        = accel

            # Lap completion detection
            if lap_count > self._last_lap_count:
                self._last_lap_count = lap_count
                t["lap_count"] = lap_count
                if last_lap_time and last_lap_time > 0:
                    t["last_lap_time"] = last_lap_time
                    t["lap_times"].append(last_lap_time)

            if obstacle_event:
                t["obstacle_events"].append((cycle_count, *obstacle_event))

            # Accel spike detection (lateral accel > threshold = spinout candidate)
            lateral_accel = abs(accel[0])
            if lateral_accel > 8.0:
                t["accel_spike_events"].append((cycle_count, lateral_accel))

            if hit and hit != "none":
                t["hit_events"].append((cycle_count, hit))

    def record_stop(self, cycle_count, cte):
        with self._lock:
            self.telemetry["stop_events"].append((cycle_count, cte))

    # ── Read API (called by mission layer, slow path) ──────────────────

    def get_telemetry_snapshot(self):
        with self._lock:
            t = self.telemetry
            return {
                "phase":              t["phase"],
                "cycle_count":        t["cycle_count"],
                "cte":                t["cte"],
                "cte_mean":           _safe_mean(t["cte_history"]),
                "cte_max":            _safe_max(t["cte_history"]),
                "yaw_rate":           t["yaw_rate"],
                "speed":              t["speed"],
                "forward_vel":        t["forward_vel"],
                "lap_count":          t["lap_count"],
                "last_lap_time":      t["last_lap_time"],
                "lap_times":          list(t["lap_times"]),
                "lap_time_trend":     _lap_time_trend(t["lap_times"]),
                "obstacle_count":     len(t["obstacle_events"]),
                "accel_spike_count":  len(t["accel_spike_events"]),
                "stop_count":         len(t["stop_events"]),
                "hit_count":          len(t["hit_events"]),
            }

    def get_directives(self):
        with self._lock:
            return dict(self.directives)

    # ── Write API (called by mission layer) ────────────────────────────

    def set_directives(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if k in self.directives:
                    self.directives[k] = v

    def reset_lap_events(self):
        """Call at lap boundary to clear per-lap event lists."""
        with self._lock:
            self.telemetry["obstacle_events"].clear()
            self.telemetry["accel_spike_events"].clear()
            self.telemetry["stop_events"].clear()
            self.telemetry["hit_events"].clear()


# ── Helpers ────────────────────────────────────────────────────────────

def _safe_mean(d):
    return sum(d) / len(d) if d else 0.0

def _safe_max(d):
    return max(abs(x) for x in d) if d else 0.0

def _lap_time_trend(lap_times):
    """
    Returns: 'improving', 'degrading', 'stable', or 'insufficient_data'
    Compares mean of last 2 laps to mean of prior 2 laps.
    Requires at least 4 completed laps for a signal.
    """
    if len(lap_times) < 4:
        return "insufficient_data"
    recent = sum(lap_times[-2:]) / 2
    prior  = sum(lap_times[-4:-2]) / 2
    delta  = recent - prior
    if delta < -1.0:
        return "improving"
    if delta > 1.0:
        return "degrading"
    return "stable"