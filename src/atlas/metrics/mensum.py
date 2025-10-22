from __future__ import annotations

import os
import threading
import time
from typing import Dict, Tuple


class MensumMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self.gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self.hist: Dict[str, list] = []

    def _labels_tuple(self, **labels):
        return tuple(sorted(labels.items()))

    def inc_counter(self, name: str, value: float = 1.0, **labels):
        with self._lock:
            key = (name, self._labels_tuple(**labels))
            self.counters[key] = self.counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, **labels):
        with self._lock:
            key = (name, self._labels_tuple(**labels))
            self.gauges[key] = value

    def add_gauge(self, name: str, delta: float, **labels):
        with self._lock:
            key = (name, self._labels_tuple(**labels))
            self.gauges[key] = self.gauges.get(key, 0.0) + delta

    def to_json(self):
        # старый JSON эндпоинт
        out = {
            "counters": {f"{n}{dict(l)}": v for (n, l), v in self.counters.items()},
            "gauges": {f"{n}{dict(l)}": v for (n, l), v in self.gauges.items()},
        }
        return out

    def to_prom(self, **base_labels) -> str:
        # минимальный экспортер
        lines = []
        for (name, labels), val in self.counters.items():
            d = dict(labels)
            d.update(base_labels)
            ls = ",".join([f'{k}="{v}"' for k, v in d.items()])
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{{{ls}}} {val}")
        for (name, labels), val in self.gauges.items():
            d = dict(labels)
            d.update(base_labels)
            ls = ",".join([f'{k}="{v}"' for k, v in d.items()])
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{{{ls}}} {val}")
        return "\n".join(lines) + "\n"


_metrics_singleton: MensumMetrics | None = None


def metrics() -> MensumMetrics:
    global _metrics_singleton
    if _metrics_singleton is None:
        _metrics_singleton = MensumMetrics()
    return _metrics_singleton


# удобный алиас
metrics = metrics()
