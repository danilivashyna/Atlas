#!/usr/bin/env python3
"""
Resonance Test - Phase C Bootstrap

Мини-прогон SELF ↔ FAB resonance без касания core.py.
Эмулирует FABCore через _MockFabCore, записывает:
- identity.jsonl (heartbeat события)
- logs/resonance_trace.jsonl (метрики по тикам)

Usage:
    AURIS_SELF=on python scripts/resonance_test.py
"""
import os
import time
import json
import pathlib
from datetime import datetime, timezone

# Активируем SELF (если не установлено)
os.environ.setdefault("AURIS_SELF", "on")

# Импортируем только эксп. адаптер, core не трогаем
from orbis_fab.fab_self_bridge_exp import attach, maybe_self_tick


class _MockFabCore:
    """Мини-шима для локального прогона без реального FABCore."""

    def __init__(self):
        self.current_tick = 0

    def get_state_snapshot(self):
        """Эмуляция малых колебаний + редких всплесков."""
        self.current_tick += 1
        return {
            "tick": self.current_tick,
            "stability": 0.82 + (0.03 if self.current_tick % 120 == 0 else 0.0),
            "oscillation_rate": 0.05 if self.current_tick % 90 else 0.15,
            "load": 0.4 + (0.2 if self.current_tick % 200 == 0 else 0.0),
        }


def main():
    """Запуск 500 тиков с записью heartbeat + resonance trace."""
    # Создаём директорию для логов
    out = pathlib.Path("logs")
    out.mkdir(parents=True, exist_ok=True)

    # Инициализируем mock FAB + SELF manager
    fab = _MockFabCore()
    self_mgr = attach(fab)  # создает/возвращает SelfManager

    if self_mgr is None:
        print("⚠️  AURIS_SELF=off, адаптер отключён. Установите AURIS_SELF=on")
        return

    token_id = "fab-default"

    # Открываем trace для записи
    trace_path = out / "resonance_trace.jsonl"
    with trace_path.open("a", encoding="utf-8") as fh:
        for i in range(500):  # ~быстрый смоук
            maybe_self_tick(fab, self_mgr, token_id=token_id)

            # Получаем актуальные метрики из токена
            token = self_mgr.get_token(token_id)
            if token is None:
                continue

            scores = token.as_dict()

            # Записываем метрики в resonance trace
            fh.write(
                json.dumps(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "phase": "C1",  # наблюдение/согласование
                        "presence": round(scores["presence"], 3),
                        "coherence": round(scores["coherence"], 3),
                        "continuity": round(scores["continuity"], 3),
                        "stress": round(scores["stress"], 3),
                        "action": "observe",
                    }
                )
                + "\n"
            )

            # Малая задержка для эмуляции реального времени
            time.sleep(0.01)

            # Прогресс каждые 100 итераций
            if (i + 1) % 100 == 0:
                print(f"Tick {i+1}/500 | presence={scores['presence']:.3f} coherence={scores['coherence']:.3f}")

    print(f"\n✅ OK • trace: {trace_path} / identity: data/identity.jsonl")
    print("   Проверьте логи для валидации Phase C bootstrap")


if __name__ == "__main__":
    main()
