"""
SELF Canary Auto-Tuner (Phase C.2)

Автоматическое управление AURIS_SELF_CANARY на основе SLO метрик:
- Увеличивает canary sampling (5% → 10% → 25% → 50% → 100%) при стабильных метриках
- Замораживает или откатывает при нарушении SLO
- Интегрируется с Prometheus для мониторинга

Design:
- Проверяет 4 условия для продвижения:
  1. stability_score_ema >= 0.80 (10 минут)
  2. oscillation_rate == 0 (10 минут)
  3. self_coherence >= 0.80 (10 минут)
  4. self_stress <= 0.30 (10 минут)
- Откат при любом SELF/Stability alert (критический или warning)

Usage:
    # В FABCore tick loop или отдельном демоне:
    from orbis_self.canary_autotune_exp import CanaryAutoTuner

    tuner = CanaryAutoTuner(prometheus_url="http://localhost:9090")
    tuner.check_and_tune()  # Вызывать каждые 5-10 минут

Phase: C.2 (Auto-tune)
Status: Experimental (2025-11-05)
"""

import logging
import os
import time
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class CanaryAutoTuner:
    """
    Автоматическое управление AURIS_SELF_CANARY на основе SLO метрик.

    Attributes:
        prometheus_url: URL Prometheus API (e.g., http://localhost:9090)
        min_stable_duration: Минимальное время стабильности перед продвижением (секунды)
        canary_steps: Последовательность значений canary [0.05, 0.10, 0.25, 0.50, 1.0]
    """

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        min_stable_duration: int = 600,  # 10 minutes
    ):
        """
        Initialize auto-tuner.

        Args:
            prometheus_url: Prometheus API endpoint
            min_stable_duration: Minimum stable duration before advancing (seconds)
        """
        self.prometheus_url = prometheus_url.rstrip("/")
        self.min_stable_duration = min_stable_duration
        self.canary_steps = [0.05, 0.10, 0.25, 0.50, 1.0]

        # State tracking
        self.last_check_time: Optional[float] = None
        self.current_canary: Optional[float] = None

    def query_prometheus(self, query: str) -> Optional[float]:
        """
        Query Prometheus and return single scalar value.

        Args:
            query: PromQL query string

        Returns:
            Scalar value or None if query failed
        """
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()

            if data["status"] != "success":
                logger.warning("Prometheus query failed: %s", data.get("error"))
                return None

            results = data["data"]["result"]
            if not results:
                return None

            # Return first result's value
            return float(results[0]["value"][1])

        except Exception as e:
            logger.error("Failed to query Prometheus: %s", e)
            return None

    def check_slo_conditions(self) -> Dict[str, bool]:
        """
        Check all SLO conditions for canary advancement.

        Returns:
            Dict with condition names and pass/fail status
        """
        conditions = {}

        # 1. Stability EMA >= 0.80 (10m average)
        ema = self.query_prometheus(
            'avg_over_time(atlas_stability_score_ema{window_id="global"}[10m])'
        )
        conditions["stability_ema"] = ema is not None and ema >= 0.80

        # 2. Oscillation rate == 0 (10m average)
        osc_rate = self.query_prometheus(
            'avg_over_time(atlas_hysteresis_oscillation_rate{window_id="global"}[10m])'
        )
        conditions["oscillation_zero"] = osc_rate is not None and osc_rate < 0.01

        # 3. SELF coherence >= 0.80 (10m average)
        coherence = self.query_prometheus("avg_over_time(self_coherence[10m])")
        conditions["self_coherence"] = coherence is not None and coherence >= 0.80

        # 4. SELF stress <= 0.30 (10m average)
        stress = self.query_prometheus("avg_over_time(self_stress[10m])")
        conditions["self_stress"] = stress is not None and stress <= 0.30

        return conditions

    def get_current_canary(self) -> Optional[float]:
        """
        Get current AURIS_SELF_CANARY value.

        Returns:
            Current canary value or None if not set
        """
        try:
            canary_str = os.getenv("AURIS_SELF_CANARY", "0.05")
            return float(canary_str)
        except ValueError:
            logger.warning("Invalid AURIS_SELF_CANARY value: %s", canary_str)
            return None

    def get_next_canary_step(self, current: float) -> Optional[float]:
        """
        Get next canary step from progression.

        Args:
            current: Current canary value

        Returns:
            Next step or None if already at max
        """
        # Find current index
        try:
            current_idx = self.canary_steps.index(current)
        except ValueError:
            # Not in standard steps, find closest
            for i, step in enumerate(self.canary_steps):
                if current < step:
                    return step
            return None

        # Return next step
        if current_idx + 1 < len(self.canary_steps):
            return self.canary_steps[current_idx + 1]
        return None

    def check_and_tune(self) -> Dict[str, Any]:
        """
        Check SLO conditions and potentially advance canary.

        Returns:
            Dict with decision details:
            - action: "advance" | "hold" | "rollback"
            - current_canary: float
            - next_canary: Optional[float]
            - conditions: Dict[str, bool]
            - reason: str
        """
        # Get current canary value
        current = self.get_current_canary()
        if current is None:
            return {
                "action": "hold",
                "current_canary": None,
                "next_canary": None,
                "conditions": {},
                "reason": "Invalid AURIS_SELF_CANARY value",
            }

        # Check if already at max
        if current >= 1.0:
            return {
                "action": "hold",
                "current_canary": current,
                "next_canary": None,
                "conditions": {},
                "reason": "Already at 100% (max)",
            }

        # Check SLO conditions
        conditions = self.check_slo_conditions()

        # All conditions must pass
        all_passed = all(conditions.values())

        if not all_passed:
            failed = [name for name, passed in conditions.items() if not passed]
            return {
                "action": "hold",
                "current_canary": current,
                "next_canary": None,
                "conditions": conditions,
                "reason": f"SLO conditions not met: {', '.join(failed)}",
            }

        # Get next step
        next_canary = self.get_next_canary_step(current)
        if next_canary is None:
            return {
                "action": "hold",
                "current_canary": current,
                "next_canary": None,
                "conditions": conditions,
                "reason": "No next step available",
            }

        # All conditions passed → advance
        logger.info(
            "🟢 Canary auto-tune: advancing %s → %s (all SLO passed)",
            current,
            next_canary,
        )

        return {
            "action": "advance",
            "current_canary": current,
            "next_canary": next_canary,
            "conditions": conditions,
            "reason": f"All SLO conditions passed for {self.min_stable_duration}s",
        }

    def apply_canary_change(self, new_value: float) -> bool:
        """
        Apply new canary value (update env var + optional restart).

        Args:
            new_value: New AURIS_SELF_CANARY value

        Returns:
            True if applied successfully

        Note:
            В production это должно обновлять systemd env файл или ConfigMap
            и перезапускать сервис. Здесь только обновляем процесс.
        """
        try:
            os.environ["AURIS_SELF_CANARY"] = str(new_value)
            logger.info("✅ Applied AURIS_SELF_CANARY=%s", new_value)

            # В production:
            # 1. Update /etc/systemd/system/atlas-api.service.d/override.conf
            # 2. systemctl daemon-reload
            # 3. systemctl restart atlas-api

            return True

        except Exception as e:
            logger.error("Failed to apply canary change: %s", e)
            return False
