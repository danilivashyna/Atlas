"""
Tests for Atlas Homeostasis Decision Engine (E4.2)

Проверяет:
- Anti-flapping (cooldowns между действиями)
- Rate-limits (ограничения на количество действий)
- Priority resolution (разрешение конфликтов)
- Детерминизм (одинаковые входы → одинаковый выход)
- Интеграция с PolicyEngine (E4.1)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from atlas.homeostasis.decision import ActionDecision, DecisionEngine


class TestDecisionEngine:
    """Тесты для DecisionEngine."""
    
    @pytest.fixture
    def minimal_config(self, tmp_path: Path) -> Path:
        """Создать минимальный конфиг для тестов."""
        config = {
            "version": "1.0",
            "enabled": True,
            "global_limits": {
                "max_actions_per_hour": 10,
                "max_concurrent": 2,
                "default_cooldown_minutes": 15,
                "dry_run": False,
            },
            "policies": [
                {
                    "name": "critical_coherence_sent_to_para",
                    "priority": "critical",
                    "enabled": True,
                    "trigger": {
                        "metric": "h_coherence_sent_to_para",
                        "operator": "<",
                        "threshold": 0.70,
                    },
                    "action": {
                        "type": "rebuild_shard",
                        "params": {"level": "sentence"},
                        "max_per_window": 1,
                        "cooldown_minutes": 30,
                    },
                },
                {
                    "name": "high_coherence_para_to_doc",
                    "priority": "high",
                    "enabled": True,
                    "trigger": {
                        "metric": "h_coherence_para_to_doc",
                        "operator": "<",
                        "threshold": 0.75,
                    },
                    "action": {
                        "type": "rebuild_shard",
                        "params": {"level": "paragraph"},
                        "max_per_window": 1,
                        "cooldown_minutes": 20,
                    },
                },
                {
                    "name": "medium_stability_drift",
                    "priority": "medium",
                    "enabled": True,
                    "trigger": {
                        "metric": "h_stability_drift",
                        "operator": ">",
                        "threshold": 0.08,
                    },
                    "action": {
                        "type": "reembed_batch",
                        "params": {"batch_size": 100},
                        "max_per_window": 1,
                        "cooldown_minutes": 10,
                    },
                },
            ],
        }
        
        config_path = tmp_path / "homeostasis.yaml"
        with config_path.open("w", encoding="utf-8") as f:
            import yaml
            yaml.dump(config, f)
        
        return config_path
    
    def test_make_decisions_no_triggers(self, minimal_config: Path, tmp_path: Path):
        """Тест: если метрики в норме — решений нет."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.85,  # > 0.70 (OK)
            "h_coherence_para_to_doc": 0.82,   # > 0.75 (OK)
            "h_stability_drift": 0.05,         # < 0.08 (OK)
        }
        
        decisions = engine.make_decisions(metrics)
        
        assert len(decisions) == 0
    
    def test_make_decisions_single_trigger(self, minimal_config: Path, tmp_path: Path):
        """Тест: одна политика срабатывает → одно решение."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,  # < 0.70 (TRIGGER!)
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
        }
        
        decisions = engine.make_decisions(metrics)
        
        assert len(decisions) == 1
        assert decisions[0].policy_name == "critical_coherence_sent_to_para"
        assert decisions[0].action.action_type == "rebuild_shard"
        assert decisions[0].action.params["level"] == "sentence"
        assert decisions[0].priority.value == "critical"
    
    def test_make_decisions_multiple_triggers_priority(self, minimal_config: Path, tmp_path: Path):
        """Тест: несколько политик срабатывают → сортировка по приоритету."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,  # critical (TRIGGER!)
            "h_coherence_para_to_doc": 0.72,   # high (TRIGGER!)
            "h_stability_drift": 0.10,         # medium (TRIGGER!)
        }
        
        decisions = engine.make_decisions(metrics)
        
        # max_concurrent=2 → только первые 2 решения
        assert len(decisions) == 2
        
        # Приоритет: critical > high > medium
        assert decisions[0].priority.value == "critical"
        assert decisions[0].policy_name == "critical_coherence_sent_to_para"
        
        assert decisions[1].priority.value == "high"
        assert decisions[1].policy_name == "high_coherence_para_to_doc"
    
    def test_cooldown_prevents_repeat(self, minimal_config: Path, tmp_path: Path):
        """Тест: cooldown предотвращает повторное выполнение."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,  # TRIGGER
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
        }
        
        # Первый вызов — решение принято
        now = datetime(2025, 10, 27, 18, 0, 0)
        decisions1 = engine.make_decisions(metrics, timestamp=now)
        assert len(decisions1) == 1
        assert decisions1[0].policy_name == "critical_coherence_sent_to_para"
        
        # Второй вызов через 10 минут (cooldown=30 минут) — решение НЕ принято
        now2 = now + timedelta(minutes=10)
        decisions2 = engine.make_decisions(metrics, timestamp=now2)
        assert len(decisions2) == 0  # cooldown ещё действует
        
        # Третий вызов через 35 минут (cooldown истёк) — решение принято
        now3 = now + timedelta(minutes=35)
        decisions3 = engine.make_decisions(metrics, timestamp=now3)
        assert len(decisions3) == 1
        assert decisions3[0].policy_name == "critical_coherence_sent_to_para"
    
    def test_rate_limit_enforcement(self, minimal_config: Path, tmp_path: Path):
        """Тест: rate-limit ограничивает количество действий в час."""
        # Изменим конфиг: max_actions_per_hour=2
        with minimal_config.open("r", encoding="utf-8") as f:
            import yaml
            config = yaml.safe_load(f)
        
        config["global_limits"]["max_actions_per_hour"] = 2
        
        with minimal_config.open("w", encoding="utf-8") as f:
            yaml.dump(config, f)
        
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,  # TRIGGER
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
        }
        
        now = datetime(2025, 10, 27, 18, 0, 0)
        
        # Первый вызов — решение принято (1/2)
        engine.clear_cooldowns()  # Сброс для чистого теста
        decisions1 = engine.make_decisions(metrics, timestamp=now)
        assert len(decisions1) == 1
        
        # Второй вызов через 5 минут — решение принято (2/2)
        engine.clear_cooldowns()
        now2 = now + timedelta(minutes=5)
        decisions2 = engine.make_decisions(metrics, timestamp=now2)
        assert len(decisions2) == 1
        
        # Третий вызов через 10 минут — rate-limit исчерпан (0/2)
        engine.clear_cooldowns()
        now3 = now + timedelta(minutes=10)
        decisions3 = engine.make_decisions(metrics, timestamp=now3)
        assert len(decisions3) == 0  # rate-limit exceeded
        
        # Четвёртый вызов через 65 минут — новое окно (1/2)
        engine.clear_cooldowns()
        now4 = now + timedelta(minutes=65)
        decisions4 = engine.make_decisions(metrics, timestamp=now4)
        assert len(decisions4) == 1
    
    def test_conflict_resolution_same_resource(self, minimal_config: Path, tmp_path: Path):
        """Тест: конфликт ресурсов разрешается по приоритету."""
        # Создадим конфиг с двумя политиками на один ресурс (sentence shard)
        with minimal_config.open("r", encoding="utf-8") as f:
            import yaml
            config = yaml.safe_load(f)
        
        # Добавим вторую политику на sentence shard (но с низким приоритетом)
        config["policies"].append({
            "name": "low_priority_sentence_rebuild",
            "priority": "low",
            "enabled": True,
            "trigger": {
                "metric": "search_latency_p95_ms",
                "operator": ">",
                "threshold": 100,
            },
            "action": {
                "type": "rebuild_shard",
                "params": {"level": "sentence"},  # Тот же ресурс!
                "max_per_window": 1,
                "cooldown_minutes": 15,
            },
        })
        
        with minimal_config.open("w", encoding="utf-8") as f:
            yaml.dump(config, f)
        
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,  # critical (TRIGGER)
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
            "search_latency_p95_ms": 150,      # low (TRIGGER)
        }
        
        decisions = engine.make_decisions(metrics)
        
        # Должно быть только 1 решение (critical), low пропущена (конфликт ресурса)
        assert len(decisions) == 1
        assert decisions[0].policy_name == "critical_coherence_sent_to_para"
        assert decisions[0].priority.value == "critical"
    
    def test_determinism_same_inputs(self, minimal_config: Path, tmp_path: Path):
        """Тест: одинаковые входы → одинаковые решения."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
            seed=42,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,
            "h_coherence_para_to_doc": 0.72,
            "h_stability_drift": 0.10,
        }
        
        now = datetime(2025, 10, 27, 18, 0, 0)
        
        # Первый прогон
        decisions1 = engine.make_decisions(metrics, timestamp=now)
        
        # Второй прогон (новый engine, те же параметры)
        engine2 = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state2",
            dry_run=True,
            seed=42,
        )
        decisions2 = engine2.make_decisions(metrics, timestamp=now)
        
        # Результаты должны совпадать
        assert len(decisions1) == len(decisions2)
        for d1, d2 in zip(decisions1, decisions2):
            assert d1.policy_name == d2.policy_name
            assert d1.action.action_type == d2.action.action_type
            assert d1.priority == d2.priority
    
    def test_execution_history(self, minimal_config: Path, tmp_path: Path):
        """Тест: история выполнения сохраняется."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
        }
        
        now = datetime(2025, 10, 27, 18, 0, 0)
        
        # Первое решение
        decisions1 = engine.make_decisions(metrics, timestamp=now)
        assert len(decisions1) == 1
        
        # Проверка истории
        history = engine.get_execution_history()
        assert len(history) == 1
        assert history[0].policy_name == "critical_coherence_sent_to_para"
        
        # Второе решение (после истечения cooldown)
        engine.clear_cooldowns()
        now2 = now + timedelta(minutes=35)
        decisions2 = engine.make_decisions(metrics, timestamp=now2)
        
        # История должна содержать оба решения
        history2 = engine.get_execution_history()
        assert len(history2) == 2
    
    def test_state_persistence(self, minimal_config: Path, tmp_path: Path):
        """Тест: состояние cooldowns сохраняется между сессиями."""
        state_dir = tmp_path / "state"
        
        metrics = {
            "h_coherence_sent_to_para": 0.65,
            "h_coherence_para_to_doc": 0.82,
            "h_stability_drift": 0.05,
        }
        
        now = datetime(2025, 10, 27, 18, 0, 0)
        
        # Первая сессия — принять решение
        engine1 = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=state_dir,
            dry_run=False,  # НЕ dry-run для сохранения состояния
        )
        decisions1 = engine1.make_decisions(metrics, timestamp=now)
        assert len(decisions1) == 1
        
        # Проверить, что состояние сохранено
        state_file = state_dir / "decision_state.json"
        assert state_file.exists()
        
        with state_file.open("r", encoding="utf-8") as f:
            state = json.load(f)
        
        assert "cooldowns" in state
        assert len(state["cooldowns"]) > 0
        
        # Вторая сессия — загрузить состояние
        engine2 = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=state_dir,
            dry_run=False,
        )
        
        # Попытка принять решение (cooldown должен быть загружен)
        now2 = now + timedelta(minutes=10)
        decisions2 = engine2.make_decisions(metrics, timestamp=now2)
        assert len(decisions2) == 0  # cooldown загружен и действует


class TestEdgeCases:
    """Тесты граничных случаев."""
    
    @pytest.fixture
    def minimal_config(self, tmp_path: Path) -> Path:
        """Создать минимальный конфиг для тестов."""
        config = {
            "version": "1.0",
            "enabled": True,
            "global_limits": {
                "max_actions_per_hour": 10,
                "max_concurrent": 2,
                "default_cooldown_minutes": 15,
            },
            "policies": [
                {
                    "name": "test_policy",
                    "priority": "medium",
                    "enabled": True,
                    "trigger": {
                        "metric": "test_metric",
                        "operator": "<",
                        "threshold": 0.70,
                    },
                    "action": {
                        "type": "test_action",
                        "params": {},
                        "max_per_window": 1,
                        "cooldown_minutes": 15,
                    },
                },
            ],
        }
        
        config_path = tmp_path / "homeostasis.yaml"
        with config_path.open("w", encoding="utf-8") as f:
            import yaml
            yaml.dump(config, f)
        
        return config_path
    
    def test_empty_metrics(self, minimal_config: Path, tmp_path: Path):
        """Тест: пустые метрики → нет решений."""
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        decisions = engine.make_decisions({})
        assert len(decisions) == 0
    
    def test_max_decisions_limit(self, minimal_config: Path, tmp_path: Path):
        """Тест: ограничение max_decisions работает."""
        # Создадим конфиг с 5 политиками
        with minimal_config.open("r", encoding="utf-8") as f:
            import yaml
            config = yaml.safe_load(f)
        
        for i in range(4):  # Добавим ещё 4 политики (всего 5)
            config["policies"].append({
                "name": f"policy_{i}",
                "priority": "medium",
                "enabled": True,
                "trigger": {
                    "metric": f"metric_{i}",
                    "operator": "<",
                    "threshold": 0.70,
                },
                "action": {
                    "type": f"action_{i}",
                    "params": {},
                    "max_per_window": 1,
                    "cooldown_minutes": 15,
                },
            })
        
        with minimal_config.open("w", encoding="utf-8") as f:
            yaml.dump(config, f)
        
        engine = DecisionEngine(
            policy_config_path=minimal_config,
            state_dir=tmp_path / "state",
            dry_run=True,
        )
        
        # Все 5 метрик триггерят политики
        metrics = {
            "test_metric": 0.60,
            "metric_0": 0.60,
            "metric_1": 0.60,
            "metric_2": 0.60,
            "metric_3": 0.60,
        }
        
        # max_decisions=3 → только 3 решения
        decisions = engine.make_decisions(metrics, max_decisions=3)
        assert len(decisions) == 3
