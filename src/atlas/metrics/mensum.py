from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Dict, Tuple


class MensumMetrics:
    def __init__(self, ns: str = "orbis_mens") -> None:
        self.ns = ns
        self._lock = threading.Lock()
        self._counters = defaultdict(float)  # (name, labels_tuple) -> value
        self._gauges = defaultdict(float)  # (name, labels_tuple) -> value
        self._hist = defaultdict(list)  # (name, labels_tuple) -> [values]

    @property
    def counters(self):
        return self._counters

    @property
    def gauges(self):
        return self._gauges

    def _lab(self, labels: dict | None) -> tuple:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def inc_counter(self, name: str, inc: float = 1.0, labels: dict | None = None, **kwargs):
        if labels is None:
            labels = {}
        else:
            labels = dict(labels)  # Make a copy to avoid mutation
        labels.update(kwargs)
        with self._lock:
            self._counters[(name, self._lab(labels))] += inc

    def set_gauge(self, name: str, value: float, labels: dict | None = None, **kwargs):
        if labels is None:
            labels = {}
        else:
            labels = dict(labels)  # Make a copy
        labels.update(kwargs)
        with self._lock:
            self._gauges[(name, self._lab(labels))] = value

    def observe_hist(self, name: str, value: float, labels: dict | None = None, **kwargs):
        if labels is None:
            labels = {}
        else:
            labels = dict(labels)  # Make a copy
        labels.update(kwargs)
        with self._lock:
            self._hist[(name, self._lab(labels))].append(value)

    def to_prom(self, **global_labels) -> str:
        global_lab = tuple(sorted(global_labels.items())) if global_labels else ()
        # text exposition format
        lines: list[str] = []
        # counters
        for (name, lab), val in self._counters.items():
            # Merge labels: convert tuple back to dict, add global labels, then back to sorted tuple (avoiding dups)
            labels_dict = dict(lab)
            labels_dict.update(global_labels)
            lab_combined = tuple(sorted(labels_dict.items()))
            lab_s = (
                ""
                if not lab_combined
                else "{" + ",".join(f'{k}="{v}"' for k, v in lab_combined) + "}"
            )
            lines.append(f"{self.ns}_{name}_total{lab_s} {val:.0f}")
        # gauges
        for (name, lab), val in self._gauges.items():
            labels_dict = dict(lab)
            labels_dict.update(global_labels)
            lab_combined = tuple(sorted(labels_dict.items()))
            lab_s = (
                ""
                if not lab_combined
                else "{" + ",".join(f'{k}="{v}"' for k, v in lab_combined) + "}"
            )
            lines.append(f"{self.ns}_{name}{lab_s} {val}")
        # simple histogram export as _sum/_count (без бакетов, достаточно для v0.5.x)
        for (name, lab), arr in self._hist.items():
            if not arr:
                continue
            labels_dict = dict(lab)
            labels_dict.update(global_labels)
            lab_combined = tuple(sorted(labels_dict.items()))
            lab_s = (
                ""
                if not lab_combined
                else "{" + ",".join(f'{k}="{v}"' for k, v in lab_combined) + "}"
            )
            lines.append(f"{self.ns}_{name}_count{lab_s} {len(arr)}")
            lines.append(f"{self.ns}_{name}_sum{lab_s} {sum(arr)}")
        return "\n".join(lines) + "\n"

    # legacy methods for compatibility
    def _labels_tuple(self, **labels):
        return tuple(sorted(labels.items()))

    def add_gauge(self, name: str, delta: float, **labels):
        with self._lock:
            key = (name, self._labels_tuple(**labels))
            self._gauges[key] = self._gauges.get(key, 0.0) + delta

    def to_json(self):
        # старый JSON эндпоинт
        out = {
            "counters": {f"{n}{dict(l)}": v for (n, l), v in self._counters.items()},
            "gauges": {f"{n}{dict(l)}": v for (n, l), v in self._gauges.items()},
        }
        return out


_metrics_singleton: MensumMetrics | None = None


def metrics() -> MensumMetrics:
    global _metrics_singleton
    if _metrics_singleton is None:
        _metrics_singleton = MensumMetrics()
    return _metrics_singleton


def metrics_ns() -> MensumMetrics:
    return metrics()


# удобный алиас
