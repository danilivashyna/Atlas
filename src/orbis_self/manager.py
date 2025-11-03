"""
SelfManager - управление жизненным циклом SELF токенов.

Основные операции:
- mint(): создание нового токена
- update(): обновление метрик существующего токена
- transfer(): передача токена другому FAB (заглушка)
- replicate(): создание копии токена с новым ID
- heartbeat(): периодическая запись состояния в identity.jsonl

Хранение: in-memory dict, персистентность через identity.jsonl.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .token import SelfToken
from .contracts import SelfEvent, SelfScores

logger = logging.getLogger(__name__)


class SelfManager:
    """
    Менеджер жизненного цикла SELF токенов.

    Хранит токены в памяти и периодически сохраняет в identity.jsonl.
    """

    def __init__(self, identity_log: Path | None = None):
        """
        Args:
            identity_log: Путь к JSONL файлу для персистентности.
                         По умолчанию: ./data/identity.jsonl
        """
        self.tokens: dict[str, SelfToken] = {}

        if identity_log is None:
            identity_log = Path("./data/identity.jsonl")

        self.identity_log = identity_log
        self._heartbeat_counter: dict[str, int] = {}  # Счётчики для heartbeat

        logger.info("SelfManager initialized, identity_log=%s", self.identity_log)

    def mint(self, token_id: str, initial_scores: SelfScores | None = None) -> SelfToken:
        """
        Создание нового SELF токена.

        Args:
            token_id: Уникальный ID токена
            initial_scores: Начальные значения метрик (опционально)

        Returns:
            Созданный SelfToken

        Raises:
            ValueError: Если токен с таким ID уже существует
        """
        if token_id in self.tokens:
            raise ValueError(f"Token {token_id!r} already exists")

        # Создаём токен с начальными значениями
        if initial_scores is None:
            initial_scores = SelfScores(
                presence=0.5,  # Нейтральное начальное состояние
                coherence=0.5,
                continuity=0.5,
                stress=0.0,
            )

        token = SelfToken(
            token_id=token_id,
            presence=initial_scores["presence"],
            coherence=initial_scores["coherence"],
            continuity=initial_scores["continuity"],
            stress=initial_scores["stress"],
            tick=0,
        )
        token.normalize()

        self.tokens[token_id] = token
        self._heartbeat_counter[token_id] = 0

        # Логируем mint событие
        self._log_event(
            SelfEvent(
                ts=self._now_iso(),
                kind="mint",
                token_id=token_id,
                data=token.as_dict(),
            )
        )

        logger.info("Minted token: %s", token)
        return token

    def update(self, token_id: str, tick: int | None = None, **scores: float) -> SelfToken:
        """
        Обновление метрик существующего токена.

        Args:
            token_id: ID токена
            tick: Номер тика (опционально)
            **scores: Частичные апдейты метрик (presence, coherence, continuity, stress)

        Returns:
            Обновлённый SelfToken

        Raises:
            KeyError: Если токен не найден

        Example:
            manager.update("fab-default", presence=0.8, stress=0.3)
        """
        if token_id not in self.tokens:
            raise KeyError(f"Token {token_id!r} not found")

        token = self.tokens[token_id]

        # Обновляем тик если передан
        if tick is not None:
            token.tick = tick

        # Обновляем метрики (безопасно, игнорирует неизвестные ключи)
        token.update_from_dict(scores)

        logger.debug("Updated token: %s", token)
        return token

    def transfer(self, token_id: str, to_fab: Any = None) -> bool:
        """
        Передача токена другому FAB компоненту (заглушка).

        В текущей версии просто логирует событие.

        Args:
            token_id: ID токена
            to_fab: Целевой FAB компонент (не используется)

        Returns:
            True если передача успешна

        Raises:
            KeyError: Если токен не найден
        """
        if token_id not in self.tokens:
            raise KeyError(f"Token {token_id!r} not found")

        token = self.tokens[token_id]

        # Логируем transfer событие
        self._log_event(
            SelfEvent(
                ts=self._now_iso(),
                kind="transfer",
                token_id=token_id,
                data={
                    "to_fab": str(to_fab) if to_fab else "unknown",
                    **token.as_dict(),
                },
            )
        )

        logger.info("Transferred token %r to %s", token_id, to_fab)
        return True

    def replicate(self, token_id: str) -> SelfToken:
        """
        Создание копии токена с новым ID.

        Args:
            token_id: ID токена для копирования

        Returns:
            Новый SelfToken с новым ID

        Raises:
            KeyError: Если исходный токен не найден
        """
        if token_id not in self.tokens:
            raise KeyError(f"Token {token_id!r} not found")

        source = self.tokens[token_id]

        # Генерируем новый ID
        replica_id = f"{token_id}:replica:{uuid4().hex[:6]}"

        # Создаём копию
        replica = SelfToken(
            token_id=replica_id,
            presence=source.presence,
            coherence=source.coherence,
            continuity=source.continuity,
            stress=source.stress,
            tick=source.tick,
            metadata=dict(source.metadata),  # Shallow copy
        )

        self.tokens[replica_id] = replica
        self._heartbeat_counter[replica_id] = 0

        # Логируем replicate событие
        self._log_event(
            SelfEvent(
                ts=self._now_iso(),
                kind="replicate",
                token_id=replica_id,
                data={
                    "source_id": token_id,
                    **replica.as_dict(),
                },
            )
        )

        logger.info("Replicated %r → %r", token_id, replica_id)
        return replica

    def heartbeat(self, token_id: str, every_n: int = 50) -> bool:
        """
        Периодическая запись состояния токена в identity.jsonl.

        Args:
            token_id: ID токена
            every_n: Частота записи (каждые N вызовов)

        Returns:
            True если запись произведена, False если пропущена

        Raises:
            KeyError: Если токен не найден
        """
        if token_id not in self.tokens:
            raise KeyError(f"Token {token_id!r} not found")

        # Инкрементируем счётчик
        self._heartbeat_counter[token_id] = self._heartbeat_counter.get(token_id, 0) + 1

        # Проверяем частоту
        if self._heartbeat_counter[token_id] % every_n != 0:
            return False

        token = self.tokens[token_id]

        # Записываем heartbeat
        self._log_event(
            SelfEvent(
                ts=self._now_iso(),
                kind="heartbeat",
                token_id=token_id,
                data={
                    "tick": token.tick,
                    "status": token.compute_status(),
                    **token.as_dict(),
                },
            )
        )

        logger.debug("Heartbeat: %r (tick=%d)", token_id, token.tick)
        return True

    def get_token(self, token_id: str) -> SelfToken | None:
        """Получение токена по ID."""
        return self.tokens.get(token_id)

    def list_tokens(self) -> list[str]:
        """Получение списка всех ID токенов."""
        return list(self.tokens.keys())

    # ─────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────

    def _log_event(self, event: SelfEvent) -> None:
        """Запись события в identity.jsonl."""
        # Создаём директорию если нужно
        self.identity_log.parent.mkdir(parents=True, exist_ok=True)

        # Append в JSONL
        with self.identity_log.open("a", encoding="utf-8") as f:
            f.write(event.to_jsonl() + "\n")

    @staticmethod
    def _now_iso() -> str:
        """Текущее время в ISO8601 UTC формате."""
        return datetime.now(timezone.utc).isoformat()


__all__ = ["SelfManager"]
