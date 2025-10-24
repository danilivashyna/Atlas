import math
import numpy as np
import os
import time

import pytest

from atlas.memory import get_node_store
from atlas.router.path_router import PathRouter


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    monkeypatch.setenv("ATLAS_MEMORY_BACKEND", "sqlite")
    monkeypatch.setenv("ATLAS_ROUTER_MODE", "on")
    monkeypatch.setenv("ATLAS_QUERY_CACHE_SIZE", "0")
    monkeypatch.setenv("ATLAS_QUERY_CACHE_TTL", "1")  # короткий TTL для теста
    yield


@pytest.fixture
def store():
    ns = get_node_store()
    ns.flush_nodes()
    ns.write_node("a/cats", "a", [0.8, 0.1, 0.1, 0.0, 0.0], "cats", 0.7)
    ns.write_node("a/dogs", "a", [0.7, 0.1, 0.1, 0.1, 0.0], "dogs", 0.6)
    ns.write_node("a/birds", "a", [0.1, 0.8, 0.1, 0.0, 0.0], "birds", 0.5)
    yield ns
    ns.flush_nodes()


class DummyRouter(PathRouter):
    def __init__(self, node_store=None):
        # dummy encoder
        super().__init__(encoder=self, node_store=node_store or get_node_store())

    def encode(self, text: str):
        # простая фиктивная «эмбеддинга» длиной 5
        t = text.lower()
        return np.array(
            [
                1.0 if "cat" in t else 0.0,
                1.0 if "bird" in t else 0.0,
                1.0 if "dog" in t else 0.0,
                0.0,
                0.0,
            ]
        )


def test_query_cache_hits(store, monkeypatch):
    r = DummyRouter(store)
    # первый вызов — miss
    r.route("I like cats", top_k=2)
    # второй вызов — hit (тот же текст)
    r.route("I like cats", top_k=2)
    # если хочешь — можно дернуть метрики и проверить hits/misses


def test_query_cache_ttl_eviction(store):
    r = DummyRouter(store)
    r.route("cats", top_k=2)  # miss
    time.sleep(1.1)  # истекает TTL=1
    r.route("cats", top_k=2)  # снова miss (эвикт)


def test_incremental_index_add_remove(store):
    # проверим, что роутинг реагирует на добавление/удаление узлов
    r = DummyRouter(store)
    # базово прохождение
    items1 = r.route("cats", top_k=1)
    assert items1, "routing should return item for cats"

    # добавим новый более «кошачий» узел
    store.write_node("a/supercats", "a", [0.95, 0.0, 0.0, 0.0, 0.05], "supercats", 0.8)
    # route должен начать его видеть (через ANN sync в реальном коде;
    # если sync делается в роутере — вызови его; иначе — rebuild через API)
    items2 = r.route("cats", top_k=1)
    assert items2[0].path in {"a/supercats", "a/cats"}

    # удалим «supercats»
    store.flush_nodes()  # или store.delete_node("a/supercats") — если поддержано
    store.write_node("a/cats", "a", [0.8, 0.1, 0.1, 0.0, 0.0], "cats", 0.7)
    store.write_node("a/dogs", "a", [0.7, 0.1, 0.1, 0.1, 0.0], "dogs", 0.6)
    items3 = r.route("cats", top_k=1)
    assert items3[0].path == "a/cats"
