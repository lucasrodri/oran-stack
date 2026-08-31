"""Small, dependency-free moving-average load classifier for KPM xApps."""

import math
import threading
from collections import deque


class LoadClassifier(object):
    """Classify a bounded moving average as idle, active or busy."""

    STATES = ("idle", "active", "busy")

    def __init__(self, window_size=5, active_threshold_kbps=1000.0,
                 busy_threshold_kbps=20000.0):
        if int(window_size) < 1:
            raise ValueError("window_size must be positive")
        if active_threshold_kbps < 0:
            raise ValueError("active threshold must be non-negative")
        if busy_threshold_kbps <= active_threshold_kbps:
            raise ValueError("busy threshold must exceed active threshold")

        self._values = deque(maxlen=int(window_size))
        self._active_threshold = float(active_threshold_kbps)
        self._busy_threshold = float(busy_threshold_kbps)
        self._state = "idle"
        self._transitions = 0
        self._samples = 0
        self._lock = threading.Lock()

    def _classify(self, average_kbps):
        if average_kbps >= self._busy_threshold:
            return "busy"
        if average_kbps >= self._active_threshold:
            return "active"
        return "idle"

    def observe(self, value_kbps):
        """Add one finite measurement and return an immutable snapshot."""
        value_kbps = float(value_kbps)
        if not math.isfinite(value_kbps):
            raise ValueError("measurement must be finite")

        with self._lock:
            self._values.append(max(0.0, value_kbps))
            self._samples += 1
            average = sum(self._values) / len(self._values)
            new_state = self._classify(average)
            changed = new_state != self._state
            if changed:
                self._state = new_state
                self._transitions += 1
            return self._snapshot(average, changed)

    def snapshot(self):
        """Return the latest state without changing the sample window."""
        with self._lock:
            average = (
                sum(self._values) / len(self._values) if self._values else 0.0
            )
            return self._snapshot(average, False)

    def _snapshot(self, average, changed):
        return {
            "average_kbps": average,
            "state": self._state,
            "state_changed": changed,
            "transitions": self._transitions,
            "samples": self._samples,
            "window_samples": len(self._values),
        }
