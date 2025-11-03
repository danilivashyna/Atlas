"""
Unit tests для SelfManager.

Проверяются:
- mint(): создание новых токенов
- update(): обновление существующих токенов
- transfer(): передача токенов (заглушка)
- replicate(): копирование токенов
- heartbeat(): периодическая запись в identity.jsonl
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.orbis_self.manager import SelfManager
from src.orbis_self.contracts import SelfScores


class TestSelfManagerMint:
    """Тесты создания токенов."""

    def test_mint_creates_token(self):
        """mint() создаёт новый токен."""
        mgr = SelfManager()

        token = mgr.mint("test-token")

        assert token is not None
        assert token.token_id == "test-token"
        assert "test-token" in mgr.tokens

    def test_mint_with_initial_scores(self):
        """mint() с начальными значениями метрик."""
        mgr = SelfManager()

        initial = SelfScores(
            presence=0.8,
            coherence=0.6,
            continuity=0.9,
            stress=0.2,
        )

        token = mgr.mint("test-token", initial_scores=initial)

        assert token.presence == 0.8
        assert token.coherence == 0.6
        assert token.continuity == 0.9
        assert token.stress == 0.2

    def test_mint_default_scores(self):
        """mint() без initial_scores использует defaults."""
        mgr = SelfManager()

        token = mgr.mint("test-token")

        # Default значения нейтральные
        assert 0.0 <= token.presence <= 1.0
        assert 0.0 <= token.coherence <= 1.0
        assert 0.0 <= token.continuity <= 1.0
        assert 0.0 <= token.stress <= 1.0

    def test_mint_duplicate_id_raises_error(self):
        """mint() с существующим ID вызывает ValueError."""
        mgr = SelfManager()
        mgr.mint("test-token")

        with pytest.raises(ValueError, match="already exists"):
            mgr.mint("test-token")

    def test_mint_writes_event_to_log(self):
        """mint() записывает событие в identity.jsonl."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=True) as f:
            log_path = Path(f.name)

        mgr = SelfManager(identity_log=log_path)
        mgr.mint("test-token")

        # Проверяем что файл создан и содержит событие
        assert log_path.exists()

        with log_path.open("r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            event = json.loads(lines[0])
            assert event["kind"] == "mint"
            assert event["token_id"] == "test-token"
            assert "presence" in event


class TestSelfManagerUpdate:
    """Тесты обновления токенов."""

    def test_update_changes_metrics(self):
        """update() обновляет метрики токена."""
        mgr = SelfManager()
        mgr.mint("test-token")

        mgr.update("test-token", presence=0.9, stress=0.1)

        token = mgr.get_token("test-token")
        assert token.presence == 0.9
        assert token.stress == 0.1

    def test_update_partial(self):
        """update() с частичными апдейтами."""
        mgr = SelfManager()
        token = mgr.mint("test-token")
        original_coherence = token.coherence

        mgr.update("test-token", presence=0.8)

        token = mgr.get_token("test-token")
        assert token.presence == 0.8
        assert token.coherence == original_coherence  # Не изменилось

    def test_update_with_tick(self):
        """update() обновляет номер тика."""
        mgr = SelfManager()
        mgr.mint("test-token")

        mgr.update("test-token", tick=1000, presence=0.7)

        token = mgr.get_token("test-token")
        assert token.tick == 1000

    def test_update_nonexistent_token_raises_error(self):
        """update() несуществующего токена вызывает KeyError."""
        mgr = SelfManager()

        with pytest.raises(KeyError, match="not found"):
            mgr.update("nonexistent", presence=0.5)

    def test_update_normalizes_values(self):
        """update() автоматически нормализует значения."""
        mgr = SelfManager()
        mgr.mint("test-token")

        mgr.update("test-token", presence=1.5, stress=-0.5)

        token = mgr.get_token("test-token")
        assert token.presence == 1.0  # Клипнут
        assert token.stress == 0.0  # Клипнут


class TestSelfManagerTransfer:
    """Тесты передачи токенов."""

    def test_transfer_returns_true(self):
        """transfer() возвращает True при успехе."""
        mgr = SelfManager()
        mgr.mint("test-token")

        result = mgr.transfer("test-token", to_fab="FAB2")

        assert result is True

    def test_transfer_nonexistent_token_raises_error(self):
        """transfer() несуществующего токена вызывает KeyError."""
        mgr = SelfManager()

        with pytest.raises(KeyError, match="not found"):
            mgr.transfer("nonexistent")

    def test_transfer_writes_event_to_log(self):
        """transfer() записывает событие в identity.jsonl."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=True) as f:
            log_path = Path(f.name)

        mgr = SelfManager(identity_log=log_path)
        mgr.mint("test-token")

        # Очищаем лог после mint
        log_path.write_text("")

        mgr.transfer("test-token", to_fab="FAB2")

        with log_path.open("r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            event = json.loads(lines[0])
            assert event["kind"] == "transfer"
            assert event["token_id"] == "test-token"


class TestSelfManagerReplicate:
    """Тесты копирования токенов."""

    def test_replicate_creates_copy(self):
        """replicate() создаёт копию токена."""
        mgr = SelfManager()
        original = mgr.mint("test-token")

        replica = mgr.replicate("test-token")

        assert replica.token_id != original.token_id
        assert replica.token_id.startswith("test-token:replica:")
        assert replica in mgr.tokens.values()

    def test_replicate_copies_metrics(self):
        """replicate() копирует метрики."""
        mgr = SelfManager()
        mgr.mint("test-token")
        mgr.update("test-token", presence=0.8, stress=0.3)

        replica = mgr.replicate("test-token")

        assert replica.presence == 0.8
        assert replica.stress == 0.3

    def test_replicate_independent_from_original(self):
        """Изменение реплики не влияет на оригинал."""
        mgr = SelfManager()
        original = mgr.mint("test-token")
        replica = mgr.replicate("test-token")

        mgr.update(replica.token_id, presence=0.9)

        assert original.presence != 0.9
        assert replica.presence == 0.9

    def test_replicate_nonexistent_token_raises_error(self):
        """replicate() несуществующего токена вызывает KeyError."""
        mgr = SelfManager()

        with pytest.raises(KeyError, match="not found"):
            mgr.replicate("nonexistent")


class TestSelfManagerHeartbeat:
    """Тесты периодической записи состояния."""

    def test_heartbeat_writes_every_n(self):
        """heartbeat() записывает каждые N вызовов."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=True) as f:
            log_path = Path(f.name)

        mgr = SelfManager(identity_log=log_path)
        mgr.mint("test-token")

        # Очищаем лог после mint
        log_path.write_text("")

        # Вызываем heartbeat 100 раз с every_n=10
        for i in range(100):
            result = mgr.heartbeat("test-token", every_n=10)

        # Должно быть 10 записей (каждые 10 вызовов)
        with log_path.open("r") as f:
            lines = f.readlines()
            assert len(lines) == 10

    def test_heartbeat_returns_true_when_written(self):
        """heartbeat() возвращает True когда запись произведена."""
        mgr = SelfManager()
        mgr.mint("test-token")

        # Первый вызов - не записывает (счётчик=1, every_n=50)
        result1 = mgr.heartbeat("test-token", every_n=50)
        assert result1 is False

        # Вызываем ещё 48 раз (итого 49)
        for _ in range(48):
            mgr.heartbeat("test-token", every_n=50)

        # 50-й вызов - записывает (счётчик=50, 50 % 50 == 0)
        result50 = mgr.heartbeat("test-token", every_n=50)
        assert result50 is True

    def test_heartbeat_event_contains_status(self):
        """heartbeat событие содержит status."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=True) as f:
            log_path = Path(f.name)

        mgr = SelfManager(identity_log=log_path)
        mgr.mint("test-token")
        mgr.update("test-token", stress=0.8)  # critical

        # Очищаем лог
        log_path.write_text("")

        # Записываем heartbeat
        mgr.heartbeat("test-token", every_n=1)

        with log_path.open("r") as f:
            event = json.loads(f.readline())
            assert event["kind"] == "heartbeat"
            assert event["status"] == "critical"

    def test_heartbeat_nonexistent_token_raises_error(self):
        """heartbeat() несуществующего токена вызывает KeyError."""
        mgr = SelfManager()

        with pytest.raises(KeyError, match="not found"):
            mgr.heartbeat("nonexistent")


class TestSelfManagerGetters:
    """Тесты вспомогательных методов."""

    def test_get_token_existing(self):
        """get_token() возвращает токен."""
        mgr = SelfManager()
        mgr.mint("test-token")

        token = mgr.get_token("test-token")

        assert token is not None
        assert token.token_id == "test-token"

    def test_get_token_nonexistent(self):
        """get_token() несуществующего токена возвращает None."""
        mgr = SelfManager()

        token = mgr.get_token("nonexistent")

        assert token is None

    def test_list_tokens_empty(self):
        """list_tokens() для пустого менеджера."""
        mgr = SelfManager()

        tokens = mgr.list_tokens()

        assert tokens == []

    def test_list_tokens_multiple(self):
        """list_tokens() возвращает все ID."""
        mgr = SelfManager()
        mgr.mint("token-1")
        mgr.mint("token-2")
        mgr.mint("token-3")

        tokens = mgr.list_tokens()

        assert set(tokens) == {"token-1", "token-2", "token-3"}
